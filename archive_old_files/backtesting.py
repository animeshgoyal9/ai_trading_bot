"""
Backtesting Framework
Tests trading strategies on historical data
"""
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import matplotlib.pyplot as plt
import config


class Backtester:
    """Backtest trading strategies on historical data"""

    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.portfolio_values = []
        self.metrics = {}

    def run_backtest(self, df, predictions, prices, confidence_scores=None):
        """
        Run backtest with model predictions

        Args:
            df: DataFrame with dates as index
            predictions: Array of buy signals (1) or hold (0)
            prices: Array of prices
            confidence_scores: Array of prediction confidence (optional)

        Returns:
            DataFrame with backtest results
        """
        logger.info("Starting backtest...")

        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.portfolio_values = []

        dates = df.index
        position_size = self.initial_capital * config.MAX_POSITION_SIZE

        for i in range(len(predictions)):
            date = dates[i]
            price = prices[i]
            signal = predictions[i]
            confidence = confidence_scores[i] if confidence_scores is not None else 1.0

            # Check if we should buy
            if signal == 1 and confidence >= config.MIN_CONFIDENCE and not self.positions:
                shares = int(position_size / price)
                cost = shares * price

                if cost <= self.capital:
                    self.positions = {
                        'shares': shares,
                        'entry_price': price,
                        'entry_date': date,
                        'stop_loss': price * (1 - config.STOP_LOSS_PERCENT),
                        'take_profit': price * (1 + config.TAKE_PROFIT_PERCENT)
                    }
                    self.capital -= cost

                    logger.debug(f"{date}: BUY {shares} shares @ ${price:.2f}")

            # Check if we should sell
            elif self.positions:
                should_sell = False
                reason = ""

                # Take profit
                if price >= self.positions['take_profit']:
                    should_sell = True
                    reason = "take_profit"

                # Stop loss
                elif price <= self.positions['stop_loss']:
                    should_sell = True
                    reason = "stop_loss"

                # Sell signal
                elif signal == 0:
                    should_sell = True
                    reason = "sell_signal"

                if should_sell:
                    shares = self.positions['shares']
                    revenue = shares * price
                    self.capital += revenue

                    profit = revenue - (shares * self.positions['entry_price'])
                    profit_pct = (price / self.positions['entry_price'] - 1) * 100

                    trade = {
                        'entry_date': self.positions['entry_date'],
                        'exit_date': date,
                        'entry_price': self.positions['entry_price'],
                        'exit_price': price,
                        'shares': shares,
                        'profit': profit,
                        'profit_pct': profit_pct,
                        'reason': reason
                    }
                    self.trades.append(trade)

                    logger.debug(f"{date}: SELL {shares} shares @ ${price:.2f} ({reason}, P&L: ${profit:.2f}, {profit_pct:.2f}%)")

                    self.positions = {}

            # Calculate portfolio value
            position_value = self.positions['shares'] * price if self.positions else 0
            total_value = self.capital + position_value
            self.portfolio_values.append({
                'date': date,
                'total_value': total_value,
                'cash': self.capital,
                'position_value': position_value
            })

        # Close any remaining positions
        if self.positions:
            final_price = prices[-1]
            shares = self.positions['shares']
            revenue = shares * final_price
            self.capital += revenue

            profit = revenue - (shares * self.positions['entry_price'])
            profit_pct = (final_price / self.positions['entry_price'] - 1) * 100

            self.trades.append({
                'entry_date': self.positions['entry_date'],
                'exit_date': dates[-1],
                'entry_price': self.positions['entry_price'],
                'exit_price': final_price,
                'shares': shares,
                'profit': profit,
                'profit_pct': profit_pct,
                'reason': 'end_of_period'
            })

            self.positions = {}

        # Calculate metrics
        self._calculate_metrics()

        logger.info(f"Backtest completed. Final capital: ${self.capital:.2f}")

        return self.get_results()

    def _calculate_metrics(self):
        """Calculate performance metrics"""
        if not self.trades:
            logger.warning("No trades executed during backtest")
            return

        trades_df = pd.DataFrame(self.trades)
        portfolio_df = pd.DataFrame(self.portfolio_values)

        # Basic metrics
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        num_trades = len(self.trades)
        winning_trades = len(trades_df[trades_df['profit'] > 0])
        losing_trades = len(trades_df[trades_df['profit'] < 0])
        win_rate = winning_trades / num_trades * 100 if num_trades > 0 else 0

        avg_profit = trades_df['profit'].mean()
        avg_win = trades_df[trades_df['profit'] > 0]['profit'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['profit'] < 0]['profit'].mean() if losing_trades > 0 else 0

        # Risk metrics
        returns = portfolio_df['total_value'].pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 else 0

        cumulative_returns = (portfolio_df['total_value'] / self.initial_capital - 1)
        running_max = cumulative_returns.cummax()
        drawdown = cumulative_returns - running_max
        max_drawdown = drawdown.min() * 100

        self.metrics = {
            'total_return': total_return,
            'total_return_pct': total_return,
            'num_trades': num_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_capital': self.capital
        }

    def get_results(self):
        """Get backtest results as DataFrame"""
        return {
            'metrics': self.metrics,
            'trades': pd.DataFrame(self.trades),
            'portfolio': pd.DataFrame(self.portfolio_values)
        }

    def print_summary(self):
        """Print backtest summary"""
        logger.info("\n" + "="*50)
        logger.info("BACKTEST SUMMARY")
        logger.info("="*50)

        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Capital:   ${self.metrics['final_capital']:,.2f}")
        logger.info(f"Total Return:    {self.metrics['total_return']:.2f}%")
        logger.info(f"\nTotal Trades:    {self.metrics['num_trades']}")
        logger.info(f"Winning Trades:  {self.metrics['winning_trades']}")
        logger.info(f"Losing Trades:   {self.metrics['losing_trades']}")
        logger.info(f"Win Rate:        {self.metrics['win_rate']:.2f}%")
        logger.info(f"\nAvg Profit:      ${self.metrics['avg_profit']:.2f}")
        logger.info(f"Avg Win:         ${self.metrics['avg_win']:.2f}")
        logger.info(f"Avg Loss:        ${self.metrics['avg_loss']:.2f}")
        logger.info(f"Profit Factor:   {self.metrics['profit_factor']:.2f}")
        logger.info(f"\nSharpe Ratio:    {self.metrics['sharpe_ratio']:.2f}")
        logger.info(f"Max Drawdown:    {self.metrics['max_drawdown']:.2f}%")
        logger.info("="*50 + "\n")

    def plot_results(self, save_path='backtest_results.png'):
        """Plot backtest results"""
        results = self.get_results()
        portfolio_df = results['portfolio']
        trades_df = results['trades']

        fig, axes = plt.subplots(3, 1, figsize=(15, 12))

        # Portfolio value over time
        axes[0].plot(portfolio_df['date'], portfolio_df['total_value'], label='Portfolio Value')
        axes[0].axhline(y=self.initial_capital, color='r', linestyle='--', label='Initial Capital')
        axes[0].set_title('Portfolio Value Over Time')
        axes[0].set_xlabel('Date')
        axes[0].set_ylabel('Value ($)')
        axes[0].legend()
        axes[0].grid(True)

        # Cumulative returns
        cumulative_return = (portfolio_df['total_value'] / self.initial_capital - 1) * 100
        axes[1].plot(portfolio_df['date'], cumulative_return, label='Cumulative Return', color='green')
        axes[1].axhline(y=0, color='r', linestyle='--')
        axes[1].set_title('Cumulative Returns (%)')
        axes[1].set_xlabel('Date')
        axes[1].set_ylabel('Return (%)')
        axes[1].legend()
        axes[1].grid(True)

        # Trade profits
        if len(trades_df) > 0:
            colors = ['green' if p > 0 else 'red' for p in trades_df['profit']]
            axes[2].bar(range(len(trades_df)), trades_df['profit'], color=colors)
            axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            axes[2].set_title('Individual Trade Profits')
            axes[2].set_xlabel('Trade Number')
            axes[2].set_ylabel('Profit ($)')
            axes[2].grid(True)

        plt.tight_layout()
        plt.savefig(save_path)
        logger.info(f"Backtest plot saved to {save_path}")
        plt.close()
