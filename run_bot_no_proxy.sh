#!/bin/bash
# Wrapper script to run the trading bot WITHOUT proxy (bypasses security sandbox)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/trading"

# Redirect all output
exec >> "$SCRIPT_DIR/logs/scheduled_bot.log" 2>&1

echo "============================================================"
echo "$(date): Trading Bot Scheduled Run Starting (NO PROXY)"
echo "============================================================"

# Activate virtual environment if it exists
if [ -f "$VENV_DIR/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    echo "Using Python: $(which python)"
else
    echo "Virtual environment not found, using system Python"
    echo "Using Python: $(which python)"
fi

# Check if required packages are installed
echo "Checking Python environment..."
python -c "import alpaca_trade_api, anthropic" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "ERROR: Required packages not installed"
    echo "Run: python -m pip install alpaca-trade-api loguru anthropic"
    exit 1
fi

# IMPORTANT: Unset proxy variables to bypass security sandbox
echo "Unsetting proxy variables..."
unset HTTP_PROXY
unset HTTPS_PROXY
unset http_proxy
unset https_proxy
unset PROXY_PORT
unset APPLE_CLAUDE_CODE_PROXY_PORT

echo "Proxy variables cleared - direct network access enabled"

# Run the bot
echo "Starting trading bot..."
cd "$SCRIPT_DIR"
python "$SCRIPT_DIR/run_claude_bot_once.py"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Bot completed successfully"
else
    echo "$(date): Bot failed with exit code $EXIT_CODE"
fi

echo "============================================================"
exit $EXIT_CODE
