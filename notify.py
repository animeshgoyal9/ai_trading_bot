"""
Email notifications for trade decisions
Uses Gmail SMTP with an App Password
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER     = os.getenv('NOTIFY_EMAIL', '')
GMAIL_PASSWORD = os.getenv('NOTIFY_APP_PASSWORD', '')  # Gmail App Password


def send_portfolio_digest(account: dict, positions: dict, trades_log: list = None):
    """Send a 6-hour portfolio summary email."""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        logger.warning("Email not configured — skipping digest")
        return

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = f"📊 Portfolio Digest — {datetime.now().strftime('%b %d %I:%M %p')} — Trading Bot"

    pv  = account.get('portfolio_value', 0)
    cash = account.get('cash', 0)
    bp  = account.get('buying_power', 0)
    eq  = account.get('equity', 0)

    # Positions table rows
    pos_rows = ""
    total_pl = 0.0
    if positions:
        for sym, p in positions.items():
            pl     = p.get('unrealized_pl', 0)
            plpc   = p.get('unrealized_plpc', 0) * 100
            total_pl += pl
            color  = "green" if pl >= 0 else "red"
            bg     = "#f5f5f5" if list(positions.keys()).index(sym) % 2 == 0 else "white"
            pos_rows += (
                f'<tr style="background:{bg}">'
                f'<td><b>{sym}</b></td>'
                f'<td>{p.get("shares",0)}</td>'
                f'<td>${p.get("entry_price",0):,.2f}</td>'
                f'<td>${p.get("current_price",0):,.2f}</td>'
                f'<td>${p.get("market_value",0):,.2f}</td>'
                f'<td style="color:{color}"><b>${pl:+,.2f} ({plpc:+.1f}%)</b></td>'
                f'</tr>'
            )
    else:
        pos_rows = '<tr><td colspan="6" style="color:#999;text-align:center;">No open positions</td></tr>'

    # Trades since last digest
    trades_html = ""
    if trades_log:
        trades_html = "<h3>Trades Since Last Digest</h3><ul>"
        for t in trades_log[-20:]:
            trades_html += f"<li>{t}</li>"
        trades_html += "</ul>"
    else:
        trades_html = "<p style='color:#999'>No trades executed since last digest.</p>"

    total_color = "green" if total_pl >= 0 else "red"

    body = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:680px;">
    <h2 style="color:#2563eb">📊 Portfolio Digest</h2>
    <p style="color:#64748b">{now_str}</p>

    <table cellpadding="8" style="border-collapse:collapse;width:100%;margin-bottom:20px;">
      <tr style="background:#2563eb;color:white">
        <th>Portfolio Value</th><th>Cash</th><th>Buying Power</th><th>Total Unrealised P&L</th>
      </tr>
      <tr style="text-align:center;font-size:18px">
        <td><b>${pv:,.2f}</b></td>
        <td>${cash:,.2f}</td>
        <td>${bp:,.2f}</td>
        <td style="color:{total_color}"><b>${total_pl:+,.2f}</b></td>
      </tr>
    </table>

    <h3>Open Positions ({len(positions)})</h3>
    <table cellpadding="8" style="border-collapse:collapse;width:100%">
      <tr style="background:#1e293b;color:white">
        <th>Symbol</th><th>Shares</th><th>Entry</th><th>Current</th><th>Value</th><th>P&L</th>
      </tr>
      {pos_rows}
    </table>

    {trades_html}

    <p style="color:#999;font-size:12px;">Paper trading bot — no real money involved. Next digest in ~6 hours.</p>
    </body></html>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = GMAIL_USER
        msg['To']      = GMAIL_USER
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())

        logger.info(f"Portfolio digest sent — {len(positions)} positions, P&L ${total_pl:+,.2f}")
    except Exception as e:
        logger.error(f"Failed to send portfolio digest: {e}")


def send_trade_alert(symbol: str, action: str, price: float,
                     confidence: float, reasoning: str,
                     qty: float = None, notional: float = None):
    """Send an email alert when a trade is executed."""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        logger.warning("Email not configured — skipping notification")
        return

    action_upper = action.upper()
    emoji = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'}.get(action_upper, '')

    subject = f"{emoji} {action_upper} {symbol} @ ${price:,.2f} — Trading Bot"

    qty_line = ''
    if qty:
        qty_line = f"<tr><td><b>Quantity</b></td><td>{qty:.6f} units</td></tr>"
    if notional:
        qty_line = f"<tr><td><b>Order Value</b></td><td>${notional:,.2f}</td></tr>"

    body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px;">
    <h2 style="color: {'green' if action_upper == 'BUY' else 'red'}">{emoji} {action_upper} Order Executed</h2>
    <table cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr style="background:#f5f5f5"><td><b>Symbol</b></td><td>{symbol}</td></tr>
        <tr><td><b>Action</b></td><td>{action_upper}</td></tr>
        <tr style="background:#f5f5f5"><td><b>Price</b></td><td>${price:,.2f}</td></tr>
        {qty_line}
        <tr style="background:#f5f5f5"><td><b>Confidence</b></td><td>{confidence:.0%}</td></tr>
        <tr><td><b>Time</b></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
    </table>
    <h3>Reasoning</h3>
    <p style="background:#f9f9f9; padding:12px; border-left:4px solid #ccc;">{reasoning}</p>
    <p style="color:#999; font-size:12px;">This is a paper trading bot — no real money involved.</p>
    </body></html>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = GMAIL_USER
        msg['To']      = GMAIL_USER
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())

        logger.info(f"Email alert sent: {action_upper} {symbol}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
