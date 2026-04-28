"""
Utility functions for logging and monitoring
"""
import os
from loguru import logger
import config


def setup_logging():
    """Configure logging for the trading bot"""
    # Create logs directory
    os.makedirs('logs', exist_ok=True)

    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        lambda msg: print(msg, end=''),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=config.LOG_LEVEL,
        colorize=True
    )

    # Add file handler
    logger.add(
        config.LOG_FILE,
        rotation="1 day",
        retention="30 days",
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    )

    logger.info("Logging configured")


def log_trade(symbol, action, shares, price, reason=""):
    """Log a trade execution"""
    logger.info(f"TRADE: {action} {shares} {symbol} @ ${price:.2f} | {reason}")


def log_performance(metrics):
    """Log performance metrics"""
    logger.info("\n" + "="*50)
    logger.info("PERFORMANCE METRICS")
    logger.info("="*50)
    for key, value in metrics.items():
        if isinstance(value, float):
            logger.info(f"{key}: {value:.4f}")
        else:
            logger.info(f"{key}: {value}")
    logger.info("="*50 + "\n")
