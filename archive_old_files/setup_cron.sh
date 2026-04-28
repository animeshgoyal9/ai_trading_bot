#!/bin/bash
# Cron Setup for Trading Bot
# Sets up a cron job to run the bot at 9 AM CST on weekdays

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python)

echo "============================================================"
echo "🤖 TRADING BOT CRON SCHEDULER SETUP"
echo "============================================================"
echo ""
echo "Script directory: $SCRIPT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Create the cron job entry
# Runs at 9 AM every day (script internally checks for weekdays)
CRON_JOB="0 9 * * * cd $SCRIPT_DIR && bash $SCRIPT_DIR/run_bot_wrapper.sh"

echo "📝 Cron job to be added:"
echo "$CRON_JOB"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_bot_wrapper.sh"; then
    echo "⚠️  Trading bot cron job already exists!"
    echo ""
    echo "To view existing cron jobs:"
    echo "   crontab -l"
    echo ""
    echo "To remove and reinstall:"
    echo "   crontab -l | grep -v 'run_bot_wrapper.sh' | crontab -"
    echo "   Then run this script again"
    exit 1
fi

# Add the cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job installed successfully!"
    echo ""
    echo "📅 Schedule:"
    echo "   Time: 9:00 AM (local time - automatically CST in your timezone)"
    echo "   Days: Monday - Friday (weekdays only - checked by script)"
    echo ""
    echo "📁 Logs will be written to:"
    echo "   $SCRIPT_DIR/logs/scheduled_bot.log"
    echo ""
    echo "🔧 Useful commands:"
    echo "   View all cron jobs:"
    echo "      crontab -l"
    echo ""
    echo "   View recent logs:"
    echo "      tail -f $SCRIPT_DIR/logs/scheduled_bot.log"
    echo ""
    echo "   Remove the scheduled job:"
    echo "      crontab -l | grep -v 'run_bot_wrapper.sh' | crontab -"
    echo ""
    echo "   Test run manually:"
    echo "      python run_claude_bot_once.py"
    echo ""
    echo "⚠️  Important Notes:"
    echo "   • Your computer must be awake at 9 AM for the job to run"
    echo "   • The bot will only trade on weekdays (Mon-Fri)"
    echo "   • Make sure your .env file has valid API keys"
    echo "   • This runs in the background - terminal doesn't need to stay open"
    echo ""
    echo "============================================================"
else
    echo "❌ Failed to install cron job"
    echo ""
    echo "You can add it manually:"
    echo "1. Run: crontab -e"
    echo "2. Add this line:"
    echo "   $CRON_JOB"
    echo "3. Save and exit"
fi
