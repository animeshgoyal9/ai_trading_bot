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
