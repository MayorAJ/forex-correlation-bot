"""
FX Correlation Telegram Bot
============================
Send two or more fx pairs to the bot and it returns
the correlation between each pair based on 14 days of daily closes.

Usage (in Telegram):
  EURUSD GBPUSD NZDCHF
  or
  EURUSD GBPUSD

Setup:
  1. pip install yfinance requests
  2. Fill in TELEGRAM_BOT_TOKEN below
  3. Run: python fx_correlation_bot.py
"""

import requests
import logging
import time
import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from itertools import combinations

# ---------------------------------------------
# CONFIG
# ---------------------------------------------
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LOOKBACK_DAYS      = 14
POLL_INTERVAL      = 2  # seconds between polling for new messages

# ---------------------------------------------
# LOGGING
# ---------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("correlation_bot.log")
    ]
)
log = logging.getLogger(__name__)


# ---------------------------------------------
# CORRELATION LABEL
# ---------------------------------------------
def correlation_label(r):
    abs_r = abs(r)
    if abs_r >= 0.85:
        strength = "Very strong"
    elif abs_r >= 0.65:
        strength = "Strong"
    elif abs_r >= 0.40:
        strength = "Moderate"
    elif abs_r >= 0.20:
        strength = "Weak"
    else:
        strength = "Very weak / none"

    direction = "positive" if r >= 0 else "negative"
    return f"{strength} {direction}"


# ---------------------------------------------
# FETCH CORRELATION
# ---------------------------------------------
def get_correlation(pairs: list[str]) -> str:
    """
    Given a list of pair strings like ['EURUSD', 'GBPUSD', 'NZDCHF'],
    fetch 14D of daily closes from Yahoo Finance and return
    a formatted correlation message.
    """
    # Convert to Yahoo Finance format e.g. EURUSD -> EURUSD=X
    tickers = {p.upper(): f"{p.upper()}=X" for p in pairs}

    try:
        data = yf.download(
            list(tickers.values()),
            period=f"{LOOKBACK_DAYS + 5}d",  # fetch a few extra days as buffer
            interval="1d",
            auto_adjust=True,
            progress=False,
        )

        # Extract close prices
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data[["Close"]]
            closes.columns = list(tickers.values())

        # Rename columns back to pair names
        reverse = {v: k for k, v in tickers.items()}
        closes  = closes.rename(columns=reverse)

        # Drop rows with any NaN and take last LOOKBACK_DAYS rows
        closes = closes.dropna().tail(LOOKBACK_DAYS)

        if len(closes) < 5:
            return "❌ Not enough data to calculate correlation. Check pair names and try again."

        # Calculate pairwise correlations
        lines = [f"📊 <b>Correlation ({len(closes)}D daily closes)</b>\n"]
        for p1, p2 in combinations(closes.columns, 2):
            r = closes[p1].corr(closes[p2])
            label = correlation_label(r)
            lines.append(f"<b>{p1} vs {p2}</b>: {r:+.2f} — {label}")

        return "\n".join(lines)

    except Exception as e:
        log.error(f"Correlation error: {e}")
        return "❌ Error fetching data. Check pair names and try again."


# ---------------------------------------------
# PARSE PAIRS FROM MESSAGE
# ---------------------------------------------
def parse_pairs(text: str) -> list[str]:
    """
    Extract valid-looking fx pair names from a message.
    Accepts space or comma separated input.
    e.g. 'EURUSD GBPUSD NZDCHF' or 'eurusd, gbpusd'
    """
    tokens = text.upper().replace(",", " ").split()
    # Basic validation — pairs are typically 6 characters
    pairs = [t for t in tokens if 4 <= len(t) <= 7 and t.isalpha()]
    return pairs


# ---------------------------------------------
# TELEGRAM POLLING
# ---------------------------------------------
def send_message(chat_id: int, text: str):
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log.error(f"Send error: {e}")


def get_updates(offset: int = None) -> list:
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params  = {"timeout": 30, "offset": offset}
    try:
        resp = requests.get(url, params=params, timeout=35)
        return resp.json().get("result", [])
    except Exception as e:
        log.error(f"getUpdates error: {e}")
        return []


def main():
    log.info("FX Correlation Bot started. Listening for messages...")
    offset = None

    while True:
        updates = get_updates(offset)

        for update in updates:
            offset = update["update_id"] + 1

            message = update.get("message", {})
            text    = message.get("text", "").strip()
            chat_id = message.get("chat", {}).get("id")

            if not text or not chat_id:
                continue

            # Help message
            if text.lower() in ["/start", "/help"]:
                send_message(chat_id,
                    "👋 <b>FX Correlation Bot</b>\n\n"
                    "Send me 2 or more fx pairs and I'll calculate their correlation "
                    f"based on the last {LOOKBACK_DAYS} days of daily closes.\n\n"
                    "<b>Example:</b>\n"
                    "EURUSD GBPUSD NZDCHF\n\n"
                    "Pairs can be space or comma separated."
                )
                continue

            pairs = parse_pairs(text)

            if len(pairs) < 2:
                send_message(chat_id,
                    "⚠️ Please send at least 2 fx pairs.\n"
                    "Example: <code>EURUSD GBPUSD</code>"
                )
                continue

            if len(pairs) > 6:
                send_message(chat_id, "⚠️ Maximum 6 pairs at a time.")
                continue

            send_message(chat_id, f"⏳ Fetching correlation for: {', '.join(pairs)}...")
            log.info(f"Calculating correlation for: {pairs}")

            result = get_correlation(pairs)
            send_message(chat_id, result)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()