#!/bin/bash
# Wrapper script to run the trading bot with proper error handling

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/scheduled_bot_error.log"
VENV_DIR="$SCRIPT_DIR/trading"

# Redirect all output
exec >> "$SCRIPT_DIR/logs/scheduled_bot.log" 2>&1

echo "============================================================"
echo "$(date): Trading Bot Scheduled Run Starting"
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
    echo ""
    echo "Attempting to install packages..."

    # Try to install packages
    python -m pip install --user alpaca-trade-api loguru anthropic 2>&1

    if [ $? -ne 0 ]; then
        echo "FAILED: Could not install packages (network issue?)"
        echo "Please install manually when on a network that allows pip:"
        echo "  python -m pip install alpaca-trade-api loguru anthropic"
        exit 1
    fi

    echo "Packages installed successfully"
fi

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
