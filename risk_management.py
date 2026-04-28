"""
Risk Management Module
Manages position sizing, stop losses, and portfolio risk
"""
import numpy as np
from loguru import logger
import config


class RiskManager:
    """Manages trading risk and position sizing"""

    def __init__(self, total_capital):
        self.total_capital = total_capital
        self.max_position_size = config.MAX_POSITION_SIZE
        self.stop_loss_pct = config.STOP_LOSS_PERCENT
        self.take_profit_pct = config.TAKE_PROFIT_PERCENT

    def calculate_position_size(self, price, confidence=1.0):
        """
        Calculate optimal position size

        Args:
            price: Current stock price
            confidence: Model prediction confidence (0-1)

        Returns:
            Number of shares to buy
        """
        # Base position size as percentage of capital
        base_position_value = self.total_capital * self.max_position_size

        # Adjust based on confidence
        adjusted_position_value = base_position_value * confidence

        # Calculate number of shares
        shares = int(adjusted_position_value / price)

        logger.debug(f"Position size: {shares} shares @ ${price:.2f} (confidence: {confidence:.2f})")

        return shares

    def calculate_stop_loss(self, entry_price):
        """Calculate stop loss price with minimum margin for Alpaca API"""
        stop_loss = entry_price * (1 - self.stop_loss_pct)
        # Ensure at least $0.01 below entry price
        stop_loss = min(entry_price - 0.01, round(stop_loss, 2))
        return stop_loss

    def calculate_take_profit(self, entry_price):
        """Calculate take profit price with minimum margin for Alpaca API"""
        take_profit = entry_price * (1 + self.take_profit_pct)
        # Ensure at least $0.01 above entry price and round properly
        take_profit = max(entry_price + 0.01, round(take_profit, 2))
        # Add small buffer for market order slippage
        take_profit = round(take_profit + 0.01, 2)
        return take_profit

    def check_portfolio_risk(self, positions, current_prices):
        """
        Check if portfolio risk is within limits

        Args:
            positions: Dict of current positions
            current_prices: Dict of current prices

        Returns:
            Boolean indicating if risk is acceptable
        """
        if not positions:
            return True

        total_position_value = sum(
            pos['shares'] * current_prices.get(symbol, pos['entry_price'])
            for symbol, pos in positions.items()
        )

        risk_exposure = total_position_value / self.total_capital

        if risk_exposure > config.MAX_POSITION_SIZE * 2:  # Max 2 positions at once
            logger.warning(f"Portfolio risk too high: {risk_exposure:.2%}")
            return False

        return True

    def should_exit_position(self, position, current_price):
        """
        Determine if position should be exited

        Args:
            position: Dict with position details
            current_price: Current stock price

        Returns:
            Tuple (should_exit, reason)
        """
        entry_price = position['entry_price']
        stop_loss = position.get('stop_loss', self.calculate_stop_loss(entry_price))
        take_profit = position.get('take_profit', self.calculate_take_profit(entry_price))

        # Check stop loss
        if current_price <= stop_loss:
            return True, 'stop_loss'

        # Check take profit
        if current_price >= take_profit:
            return True, 'take_profit'

        return False, None

    def calculate_kelly_criterion(self, win_rate, avg_win, avg_loss):
        """
        Calculate optimal position size using Kelly Criterion

        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount

        Returns:
            Optimal position size as fraction of capital
        """
        if avg_loss == 0:
            return 0

        win_loss_ratio = abs(avg_win / avg_loss)
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        # Use half Kelly for safety
        kelly_fraction = max(0, min(kelly * 0.5, self.max_position_size))

        logger.debug(f"Kelly Criterion: {kelly_fraction:.2%}")
        return kelly_fraction

    def calculate_var(self, returns, confidence_level=0.95):
        """
        Calculate Value at Risk (VaR)

        Args:
            returns: Array of portfolio returns
            confidence_level: Confidence level for VaR

        Returns:
            VaR value
        """
        if len(returns) == 0:
            return 0

        var = np.percentile(returns, (1 - confidence_level) * 100)
        logger.debug(f"VaR ({confidence_level:.0%}): {var:.4f}")
        return var
