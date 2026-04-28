"""
Train Model Script with Sentiment Analysis
Trains the ML model on historical data + sentiment
"""
import sys
from loguru import logger
from data_collector import DataCollector
from feature_engineering import FeatureEngine
from ml_model import TradingModel, prepare_train_test_data
from backtesting import Backtester
import config
from utils import setup_logging


def train_model_with_sentiment(symbol='AAPL', save_model=True):
    """
    Train the trading model with sentiment analysis

    Args:
        symbol: Stock symbol to train on
        save_model: Whether to save the trained model
    """
    logger.info(f"Training sentiment-enhanced model for {symbol}")
    logger.info(f"Sentiment enabled: {config.USE_SENTIMENT}")

    # 1. Collect data
    logger.info("Step 1: Collecting historical data...")
    collector = DataCollector()
    df = collector.fetch_historical_data(symbol)

    if df is None or df.empty:
        logger.error(f"No data available for {symbol}")
        return None

    logger.info(f"Collected {len(df)} records")

    # 2. Engineer features (with sentiment)
    logger.info("Step 2: Engineering features...")
    feature_engine = FeatureEngine(use_sentiment=config.USE_SENTIMENT)

    # Add technical indicators
    df_features = feature_engine.add_technical_indicators(df)

    # Add sentiment features
    if config.USE_SENTIMENT:
        logger.info("Step 2b: Adding sentiment features...")
        df_features = feature_engine.add_sentiment_features(df_features, symbol)

    # Create target
    df_features = feature_engine.create_target(df_features, horizon=1, threshold=0.01)

    logger.info(f"Created {len(df_features.columns)} total features")

    # 3. Prepare train/test data
    logger.info("Step 3: Preparing train/test data...")
    feature_cols = feature_engine.select_features(df_features)

    logger.info(f"Using {len(feature_cols)} features for training:")
    logger.info(f"  Technical features: {len([c for c in feature_cols if not c.startswith('sentiment_')])}")
    logger.info(f"  Sentiment features: {len([c for c in feature_cols if c.startswith('sentiment_')])}")

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
    backtester.plot_results(f'backtest_{symbol}_sentiment.png')

    # 7. Save model
    if save_model:
        model_path = model.save_model()
        logger.info(f"Model saved to {model_path}")

    logger.info("Training complete!")

    return model, feature_engine, metrics, results


def main():
    """Main training script with sentiment"""
    setup_logging()

    logger.info("="*50)
    logger.info("AI TRADING BOT - SENTIMENT-ENHANCED TRAINING")
    logger.info("="*50)

    # Show sentiment configuration
    logger.info(f"\nSentiment Analysis: {'ENABLED' if config.USE_SENTIMENT else 'DISABLED'}")
    if config.USE_SENTIMENT:
        logger.info(f"  NewsAPI Key: {'Set' if config.NEWS_API_KEY else 'Not Set (using free sources)'}")
        logger.info(f"  Alpha Vantage Key: {'Set' if config.ALPHA_VANTAGE_KEY else 'Not Set (using free sources)'}")
        logger.info(f"  Lookback Days: {config.SENTIMENT_LOOKBACK_DAYS}")
        logger.info(f"  Sentiment Weight: {config.SENTIMENT_WEIGHT}")

    # Train on multiple stocks
    symbols = config.STOCK_UNIVERSE[:3]  # Train on first 3 stocks for demo

    for symbol in symbols:
        logger.info(f"\nTraining sentiment-enhanced model for {symbol}...")
        try:
            train_model_with_sentiment(symbol, save_model=True)
        except Exception as e:
            logger.error(f"Error training model for {symbol}: {e}")
            continue

    logger.info("\nAll training complete!")


if __name__ == "__main__":
    main()
