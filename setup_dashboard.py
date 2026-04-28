#!/usr/bin/env python3
"""
Sets up the AI Trading Dashboard to start automatically on login (macOS).

Run once:
    python setup_dashboard.py install    # install & start now
    python setup_dashboard.py uninstall  # remove
    python setup_dashboard.py status     # check if running
"""
import os, sys, subprocess
from pathlib import Path

BOT_DIR   = Path(__file__).parent.absolute()
VENV_BIN  = BOT_DIR / "trading" / "bin"
LABEL     = "com.tradingbot.dashboard"
PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST     = PLIST_DIR / f"{LABEL}.plist"
LOG_DIR   = BOT_DIR / "logs"
PORT      = 8502


def plist_content():
    streamlit = VENV_BIN / "streamlit"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>{streamlit}</string>
    <string>run</string>
    <string>{BOT_DIR / "dashboard.py"}</string>
    <string>--server.port</string>
    <string>{PORT}</string>
    <string>--server.headless</string>
    <string>true</string>
    <string>--server.runOnSave</string>
    <string>false</string>
    <string>--browser.gatherUsageStats</string>
    <string>false</string>
  </array>

  <key>WorkingDirectory</key>
  <string>{BOT_DIR}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>{LOG_DIR}/dashboard.log</string>

  <key>StandardErrorPath</key>
  <string>{LOG_DIR}/dashboard_error.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>{VENV_BIN}:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key>
    <string>{Path.home()}</string>
  </dict>
</dict>
</plist>
"""


def install():
    LOG_DIR.mkdir(exist_ok=True)
    PLIST_DIR.mkdir(parents=True, exist_ok=True)

    # Stop existing if running
    subprocess.run(["launchctl", "unload", str(PLIST)],
                   capture_output=True)

    PLIST.write_text(plist_content())
    result = subprocess.run(["launchctl", "load", str(PLIST)],
                            capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Dashboard installed as login item.")
        print(f"   It will start automatically every time you log in.")
        print(f"   Open: http://localhost:{PORT}")
    else:
        print(f"❌ Failed to load: {result.stderr}")
        sys.exit(1)


def uninstall():
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    if PLIST.exists():
        PLIST.unlink()
    print("✅ Dashboard login item removed.")


def status():
    result = subprocess.run(
        ["launchctl", "list", LABEL],
        capture_output=True, text=True)
    if result.returncode == 0:
        lines = result.stdout.strip().splitlines()
        pid_line = next((l for l in lines if '"PID"' in l or "PID" in l), "")
        print(f"✅ Running  —  http://localhost:{PORT}")
        if pid_line:
            print(f"   {pid_line.strip()}")
    else:
        print("🔴 Not running")
        print(f"   Start manually:  python {Path(__file__).name} install")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "install"
    {"install": install, "uninstall": uninstall, "status": status}.get(
        cmd, lambda: print(f"Usage: python {Path(__file__).name} install|uninstall|status")
    )()
