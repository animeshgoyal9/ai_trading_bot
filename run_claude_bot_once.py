#!/usr/bin/env python3
"""
Setup Scheduled Trading Bot
Configures the bot to run automatically at 10 AM CT on weekdays
"""
import os
import sys
from pathlib import Path


def create_launchd_plist():
    """Create macOS launchd plist file for scheduled execution"""

    # Get the absolute path to the bot directory
    bot_dir = Path(__file__).parent.absolute()
    wrapper_script = bot_dir / "run_bot_wrapper.sh"
    log_dir = bot_dir / "logs"

    # Create logs directory if it doesn't exist
    log_dir.mkdir(exist_ok=True)

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tradingbot.claude</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{wrapper_script}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{bot_dir}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>{log_dir}/scheduled_bot.log</string>

    <key>StandardErrorPath</key>
    <string>{log_dir}/scheduled_bot_error.log</string>

    <key>RunAtLoad</key>
    <false/>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:{bot_dir}</string>
    </dict>
</dict>
</plist>
"""

    return plist_content


def install_launchd_job():
    """Install the launchd job for the current user"""

    # Create the plist content
    plist_content = create_launchd_plist()

    # Path to LaunchAgents directory
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    plist_file = launch_agents_dir / "com.tradingbot.claude.plist"

    # Write the plist file
    with open(plist_file, 'w') as f:
        f.write(plist_content)

    print("="*60)
    print("🤖 TRADING BOT SCHEDULER SETUP")
    print("="*60)
    print(f"\n✅ Created launchd plist file:")
    print(f"   {plist_file}")

    # Load the job
    print("\n📝 Loading the scheduled job...")
    result = os.system(f"launchctl load {plist_file}")

    if result == 0:
        print("✅ Job loaded successfully!")
        print("\n📅 Schedule:")
        print("   Time: 10:00 AM CT")
        print("   Days: Monday - Friday (weekdays only)")
        print("   The script checks weekday internally")

        print("\n📁 Logs will be written to:")
        print(f"   {Path(__file__).parent.absolute() / 'logs' / 'scheduled_bot.log'}")
        print(f"   {Path(__file__).parent.absolute() / 'logs' / 'scheduled_bot_error.log'}")

        print("\n🔧 Useful commands:")
        print("   Check if job is loaded:")
        print(f"      launchctl list | grep tradingbot")
        print("\n   View recent logs:")
        print(f"      tail -f logs/scheduled_bot.log")
        print("\n   Unload (disable) the job:")
        print(f"      launchctl unload {plist_file}")
        print("\n   Reload (after changes):")
        print(f"      launchctl unload {plist_file} && launchctl load {plist_file}")
        print("\n   Test run manually:")
        print(f"      python3 run_claude_bot_once.py")

        print("\n⚠️  Important Notes:")
        print("   • Your computer must be awake at 10 AM for the job to run")
        print("   • The bot will only trade on weekdays (Mon-Fri)")
        print("   • Make sure your .env file has valid API keys")
        print("   • This runs in the background - terminal doesn't need to stay open")

    else:
        print("❌ Failed to load job")
        print("\nTry running manually:")
        print(f"   launchctl load {plist_file}")

    print("\n" + "="*60)


def uninstall_launchd_job():
    """Uninstall the launchd job"""

    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    plist_file = launch_agents_dir / "com.tradingbot.claude.plist"

    if not plist_file.exists():
        print("❌ Job not found. Nothing to uninstall.")
        return

    print("🗑️  Uninstalling scheduled job...")

    # Unload the job
    os.system(f"launchctl unload {plist_file}")

    # Remove the plist file
    plist_file.unlink()

    print("✅ Job uninstalled successfully!")


def main():
    """Main function"""

    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall_launchd_job()
    else:
        install_launchd_job()


if __name__ == "__main__":
    main()