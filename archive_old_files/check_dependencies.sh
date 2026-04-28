#!/bin/bash
# Check and install required packages for trading bot

echo "============================================================"
echo "🔍 CHECKING TRADING BOT DEPENDENCIES"
echo "============================================================"
echo ""
echo "Python being used: $(which python)"
echo "Python version: $(python --version)"
echo ""

# List of required packages
PACKAGES=(
    "alpaca-trade-api"
    "loguru"
    "anthropic"
    "yfinance"
    "pandas"
    "numpy"
    "python-dotenv"
    "pytz"
    "scikit-learn"
    "ta"
    "joblib"
)

echo "📦 Checking installed packages..."
echo ""

MISSING=()
for package in "${PACKAGES[@]}"; do
    # Convert package name to import name (handle special cases)
    if [[ "$package" == "alpaca-trade-api" ]]; then
        import_name="alpaca_trade_api"
    elif [[ "$package" == "python-dotenv" ]]; then
        import_name="dotenv"
    elif [[ "$package" == "scikit-learn" ]]; then
        import_name="sklearn"
    else
        import_name="$package"
    fi

    if python -c "import $import_name" 2>/dev/null; then
        echo "✅ $package"
    else
        echo "❌ $package (MISSING)"
        MISSING+=("$package")
    fi
done

echo ""
if [ ${#MISSING[@]} -eq 0 ]; then
    echo "============================================================"
    echo "✅ ALL DEPENDENCIES INSTALLED!"
    echo "============================================================"
    echo ""
    echo "You can now run the bot:"
    echo "   python run_claude_bot_once.py"
    echo ""
    echo "Or set up the scheduler:"
    echo "   python setup_scheduler.py"
else
    echo "============================================================"
    echo "❌ MISSING ${#MISSING[@]} PACKAGE(S)"
    echo "============================================================"
    echo ""
    echo "Installing missing packages..."
    echo ""

    python -m pip install "${MISSING[@]}"

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Packages installed successfully!"
        echo ""
        echo "Test the bot:"
        echo "   python run_claude_bot_once.py"
    else
        echo ""
        echo "❌ Installation failed. Try manually:"
        echo "   python -m pip install ${MISSING[*]}"
    fi
fi
