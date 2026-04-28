"""
Configuration settings for the AI Trading Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca API Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

# Trading Configuration
TRADING_CAPITAL = float(os.getenv('TRADING_CAPITAL', 10000))
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', 0.1))  # 10% of capital per trade
STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', 0.02))  # 2% stop loss
TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', 0.05))  # 5% take profit

# Stock Universe - Your custom portfolio (kept for reference / manual overrides)
STOCK_UNIVERSE = [
    # Photonics / Optics
    'LITE',  # Lumentum Holdings
    'LASR',  # nLIGHT
    'COHR',  # Coherent Corp
    'AAOI',  # Applied Optoelectronics
    'LPTH',  # LightPath Technologies
    'LWLG',  # Lightwave Logic
    'FN',    # Fabrinet
    # Semiconductors
    'ALAB',  # Astera Labs
    'ANET',  # Arista Networks
    'NVDA',  # NVIDIA
    'TSM',   # Taiwan Semiconductor
    'AVGO',  # Broadcom
    'MU',    # Micron Technology
    'AMD',   # Advanced Micro Devices
    'INTC',  # Intel
    'TXN',   # Texas Instruments
    'MRVL',  # Marvell Technology
    'CRDO',  # Credo Technology
    'AMKR',  # Amkor Technology
    'PLAB',  # Photronics
    'AXTI',  # AXT Inc
    'AOSL',  # Alpha and Omega Semiconductor
    'AEHR',  # Aehr Test Systems
    'POET',  # POET Technologies
    'SKYT',  # Skywater Technology
    'CAMT',  # Camtek
    # AI / Data Infrastructure
    'VRT',   # Vertiv Holdings
    'PLTR',  # Palantir
    'APP',   # AppLovin
    'NBIS',  # Nebius Group
    'CRWV',  # CoreWeave
    'DELL',  # Dell Technologies
    'ORCL',  # Oracle
    'HPE',   # HP Enterprise
    'GLW',   # Corning
    'CIEN',  # Ciena
    'APH',   # Amphenol
    # Quantum Computing
    'IONQ',  # IonQ
    'QBTS',  # D-Wave Quantum
    'ARQQ',  # Arqit Quantum
    # Robotics / Drones / Space
    'SERV',  # Serve Robotics
    'RCAT',  # Red Cat Holdings
    'BKSY',  # BlackSky Technology
    'ASTS',  # AST SpaceMobile
    'RKLB',  # Rocket Lab
    'OUST',  # Ouster
    'VWAV',  # V2X
    # Energy / Power
    'BE',    # Bloom Energy
    # Uranium / Nuclear
    'CCJ',   # Cameco
    'UUUU',  # Energy Fuels
    'NXE',   # NexGen Energy
    'UEC',   # Uranium Energy
    'LEU',   # Centrus Energy
    # Storage / Memory
    'SNDK',  # SanDisk
    'STX',   # Seagate Technology
    'WDC',   # Western Digital
    # Precious Metals / Commodities
    'AG',    # First Majestic Silver
    'GLD',   # Gold ETF
    'COPX',  # Copper Miners ETF
    'MP',    # MP Materials
    'TMC',   # The Metals Company
    'WCP',   # Whitecap Resources
    # Crypto Mining / Blockchain
    'APLD',  # Applied Blockchain
    'CORZ',  # Core Scientific
    'CIFR',  # Cipher Mining
    'WULF',  # TeraWulf
    'IREN',  # Iris Energy
    'CRML',  # Critical Metals Corp
    # Defense / Small Cap
    'USAR',  # American Strategic Investment
    'WWR',   # Westwater Resources
    'ONDS',  # Ondas Holdings
    'OKLL',  # Okeelala? (verify ticker)
    'NUAI',  # Nu-Axess AI
    'BBAI',  # BigBear.ai
    'RXRX',  # Recursion Pharmaceuticals
    'LAES',  # SEALSQ Corp
    # Infrastructure / Industrials
    'STRL',  # Sterling Infrastructure
    'EME',   # EMCOR Group
    'ETN',   # Eaton Corp
    'PWR',   # Quanta Services
    'JBL',   # Jabil
    # ETFs
    'QQQ',   # Nasdaq 100 ETF
    'SPY',   # S&P 500 ETF
    # Large Cap
    'AAPL',  # Apple
]

# NASDAQ 100 — used as the broad scanning universe
# Pre-filter selects the best ~15 setups before AI analysis each cycle
NASDAQ_100 = [
    # Mega-cap tech
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'TSLA', 'GOOGL', 'GOOG', 'AVGO', 'NFLX',
    # Large-cap tech & semis
    'AMD', 'ADBE', 'CSCO', 'TXN', 'QCOM', 'INTC', 'MU', 'AMAT', 'LRCX', 'KLAC',
    'ADI', 'MRVL', 'NXPI', 'ON', 'ASML', 'SNPS', 'CDNS',
    # Software & cloud
    'INTU', 'PANW', 'CRWD', 'FTNT', 'ZS', 'DDOG', 'SNOW', 'WDAY', 'TEAM', 'OKTA',
    'PLTR', 'TTD', 'ANSS', 'VRSK', 'CTSH', 'MDB',
    # Consumer & e-commerce
    'COST', 'PEP', 'SBUX', 'ABNB', 'BKNG', 'EBAY', 'DLTR', 'ROST', 'LULU', 'MAR',
    'MELI',
    # Biotech & healthcare
    'AMGN', 'ISRG', 'REGN', 'VRTX', 'GILD', 'BIIB', 'IDXX', 'ILMN', 'DXCM', 'MRNA',
    'ALGN',
    # Telecom & media
    'TMUS',
    # Industrials & energy
    'PCAR', 'FAST', 'ODFL', 'CTAS', 'PAYX', 'ORLY', 'ADP', 'CPRT', 'CSGP',
    # Financials & payments
    'PYPL', 'FICO',
    # Utilities & clean energy
    'CEG', 'EXC',
    # Miscellaneous high-cap NASDAQ
    'KDP', 'MNST', 'SIRI', 'EBAY', 'EA', 'ENPH', 'GEHC', 'HON',
    # Your original picks (keep them in the scan)
    'GLD', 'SNDK', 'LITE', 'MP', 'RKLB', 'APLD', 'IREN', 'UUUU', 'TSM',
]
# De-duplicate
NASDAQ_100 = list(dict.fromkeys(NASDAQ_100))

# How many top candidates to send to AI after pre-filtering
PREFILTER_TOP_N = int(os.getenv('PREFILTER_TOP_N', 15))

# Crypto Universe - Major cryptocurrencies (use with Alpaca Crypto)
CRYPTO_UNIVERSE = [
    'BTC/USD',   # Bitcoin
    'ETH/USD',   # Ethereum
    'SOL/USD',   # Solana
    'XRP/USD',   # XRP
]

# Trading Mode - Switch between stocks and crypto
TRADING_MODE = os.getenv('TRADING_MODE', 'stocks')  # 'stocks' or 'crypto'

# Extended Hours Trading (stocks only)
ENABLE_EXTENDED_HOURS = os.getenv('ENABLE_EXTENDED_HOURS', 'false').lower() == 'true'

# Get appropriate universe based on mode
if TRADING_MODE == 'crypto':
    TRADING_UNIVERSE = CRYPTO_UNIVERSE
else:
    TRADING_UNIVERSE = STOCK_UNIVERSE

# Data Configuration
DATA_START_DATE = '2020-01-01'
LOOKBACK_PERIOD = 60  # days of historical data for features
TRAIN_TEST_SPLIT = 0.8

# Model Configuration
MODEL_TYPE = 'xgboost'  # 'xgboost', 'random_forest', 'gradient_boosting'
RETRAIN_FREQUENCY = 7  # days

# Technical Indicators Configuration
INDICATORS = {
    'sma_fast': 10,
    'sma_slow': 30,
    'ema_fast': 12,
    'ema_slow': 26,
    'rsi_period': 14,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,
    'bb_std': 2,
    'atr_period': 14,
    'adx_period': 14,
}

# Trading Hours (ET)
MARKET_OPEN = '09:30'
MARKET_CLOSE = '16:00'

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/trading_bot.log'

# Performance Thresholds
MIN_CONFIDENCE = 0.6  # Minimum prediction confidence to trade
MIN_SHARPE_RATIO = 1.0  # Minimum Sharpe ratio for strategy
MAX_DRAWDOWN = 0.15  # Maximum acceptable drawdown (15%)

# Sentiment Analysis API Keys (Optional - works without them using free sources)
NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')  # Get free key at newsapi.org
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', '')  # Get free key at alphavantage.co

# Sentiment Analysis Configuration
USE_SENTIMENT = os.getenv('USE_SENTIMENT', 'false').lower() == 'true'  # Enable/disable sentiment
SENTIMENT_LOOKBACK_DAYS = int(os.getenv('SENTIMENT_LOOKBACK_DAYS', 7))  # Days of news to analyze
SENTIMENT_WEIGHT = float(os.getenv('SENTIMENT_WEIGHT', 0.3))  # Weight of sentiment in model (0-1)

# Claude AI Agent Configuration (Optional - Gemini is default)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')  # Get key at console.anthropic.com
USE_CLAUDE_AGENT = os.getenv('USE_CLAUDE_AGENT', 'false').lower() == 'true'  # Use Claude for decisions
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')  # Claude model to use
CLAUDE_MIN_CONFIDENCE = float(os.getenv('CLAUDE_MIN_CONFIDENCE', 0.7))  # Min confidence for Claude trades

# Gemini AI Agent Configuration (Recommended - Free tier available!)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')  # Get FREE key at aistudio.google.com
USE_GEMINI_AGENT = os.getenv('USE_GEMINI_AGENT', 'true').lower() == 'true'  # Use Gemini for decisions
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash-latest')  # Gemini model to use
GEMINI_MIN_CONFIDENCE = float(os.getenv('GEMINI_MIN_CONFIDENCE', 0.7))  # Min confidence for trades
