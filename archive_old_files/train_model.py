"""
Train Model Script
Trains the ML model on historical data
"""
import sys
from loguru import logger
from data_collector import DataCollector
from feature_engineering import FeatureEngine
from ml_model import TradingModel, prepare_train_test_data
from backtesting import Backtester
import config
from utils import setup_logging


def train_model(symbol='AAPL', save_model=True):
    """
    Train the trading model

    Args:
        symbol: Stock symbol to train on
        save_model: Whether to save the trained model
    """
    logger.info(f"Training model for {symbol}")

    # 1. Collect data
    logger.info("Step 1: Collecting data...")
    collector = DataCollector()
    df = collector.fetch_historical_data(symbol)

    if df is None or df.empty:
        logger.error(f"No data available for {symbol}")
        return None

    logger.info(f"Collected {len(df)} records")

    # 2. Engineer features
    logger.info("Step 2: Engineering features...")
    feature_engine = FeatureEngine()
    df_features = feature_engine.add_technical_indicators(df)
    df_features = feature_engine.create_target(df_features, horizon=1, threshold=0.01)

    logger.info(f"Created {len(df_features.columns)} features")

    # 3. Prepare train/test data
    logger.info("Step 3: Preparing train/test data...")
    feature_cols = feature_engine.select_features(df_features)
    X_train, X_test, y_train, y_test = prepare_train_test_data(
        df_features, feature_cols, target_col='target'
    )

    # 4. Train model
    logger.info("Step 4: Training model...")
    model = TradingModel(model_type=config.MODEL_TYPE)
    model.train(X_train, y_train, X_test, y_test)

    # 5. Evaluate model
    logger.info("Step 5: Evaluating model...")
    metrics = model.evaluate(X_test, y_test)

    # 6. Backtest
    logger.info("Step 6: Running backtest...")
    backtester = Backtester(initial_capital=config.TRADING_CAPITAL)

    # Get predictions for test set
    predictions = model.predict(X_test)
    confidence_scores = model.predict_proba(X_test)[:, 1]
    prices = df_features.loc[X_test.index, 'close'].values

    results = backtester.run_backtest(
        df_features.loc[X_test.index],
        predictions,
        prices,
        confidence_scores
    )

    backtester.print_summary()
    backtester.plot_results(f'backtest_{symbol}.png')

    # 7. Save model
    if save_model:
        model_path = model.save_model()
        logger.info(f"Model saved to {model_path}")

    logger.info("Training complete!")

    return model, feature_engine, metrics, results


def main():
    """Main training script"""
    setup_logging()

    logger.info("="*50)
    logger.info("AI TRADING BOT - MODEL TRAINING")
    logger.info("="*50)

    # Train on multiple stocks
    symbols = config.STOCK_UNIVERSE[:3]  # Train on first 3 stocks for demo

    for symbol in symbols:
        logger.info(f"\nTraining model for {symbol}...")
        try:
            train_model(symbol, save_model=True)
        except Exception as e:
            logger.error(f"Error training model for {symbol}: {e}")
            continue

    logger.info("\nAll training complete!")


if __name__ == "__main__":
    main()
