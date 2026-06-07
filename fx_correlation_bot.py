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
  1. pip install requests python-dotenv
  2. Add TELEGRAM_BOT_TOKEN to your .env file
  3. Run: python fx_correlation_bot.py
"""

import requests
import logging
import time
import os
from datetime import datetime, timedelta
from itertools import combinations
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------
# CONFIG
# ---------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LOOKBACK_DAYS      = 14
POLL_INTERVAL      = 2  # seconds between polling

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
# FETCH RATES FROM FRANKFURTER
# ---------------------------------------------
def fetch_rates(base: str, symbols: list, start_date: str, end_date: str) -> dict:
    """
    Fetch historical daily rates from Frankfurter API.
    Returns dict of {date: {currency: rate}}
    """
    url = f"https://api.frankfurter.dev/v1/{start_date}..{end_date}"
    params = {
        "base": base,
        "symbols": ",".join(symbols)
    }
    resp = requests.get(url, params=params, timeout=15)
    data = resp.json()
    return data.get("rates", {})


def get_pair_closes(pair: str, start_date: str, end_date: str) -> dict:
    """
    Get daily closes for a forex pair like EURUSD.
    Splits into base (EUR) and quote (USD), fetches base rates,
    returns {date: rate} for the pair.
    """
    base  = pair[:3].upper()
    quote = pair[3:].upper()

    rates = fetch_rates(base, [quote], start_date, end_date)

    closes = {}
    for date, day_rates in rates.items():
        if quote in day_rates:
            closes[date] = day_rates[quote]
    return closes


# ---------------------------------------------
# FETCH CORRELATION
# ---------------------------------------------
def get_correlation(pairs: list) -> str:
    end_date   = datetime.utcnow().date()
    # Fetch extra days to account for weekends/holidays
    start_date = end_date - timedelta(days=LOOKBACK_DAYS + 10)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str   = end_date.strftime("%Y-%m-%d")

    # Fetch closes for each pair
    pair_closes = {}
    for pair in pairs:
        try:
            closes = get_pair_closes(pair, start_str, end_str)
            if len(closes) < 5:
                return f"❌ Not enough data for <b>{pair}</b>. Check the pair name and try again."
            pair_closes[pair] = closes
        except Exception as e:
            log.error(f"Error fetching {pair}: {e}")
            return f"❌ Error fetching data for <b>{pair}</b>. Try again."

    # Find common dates across all pairs
    common_dates = sorted(
        set.intersection(*[set(v.keys()) for v in pair_closes.values()])
    )

    # Take last LOOKBACK_DAYS common dates
    common_dates = common_dates[-LOOKBACK_DAYS:]

    if len(common_dates) < 5:
        return "❌ Not enough overlapping data across pairs. Try again."

    # Build price series
    series = {pair: [pair_closes[pair][d] for d in common_dates] for pair in pairs}

    # Calculate pairwise correlations
    def pearson(x, y):
        n    = len(x)
        mx   = sum(x) / n
        my   = sum(y) / n
        num  = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        den  = (sum((x[i] - mx) ** 2 for i in range(n)) *
                sum((y[i] - my) ** 2 for i in range(n))) ** 0.5
        return num / den if den != 0 else 0.0

    lines = [f"📊 <b>Correlation ({len(common_dates)}D daily closes)</b>\n"]
    for p1, p2 in combinations(pairs, 2):
        r     = pearson(series[p1], series[p2])
        label = correlation_label(r)
        lines.append(f"<b>{p1} vs {p2}</b>: {r:+.2f} — {label}")

    return "\n".join(lines)


# ---------------------------------------------
# PARSE PAIRS FROM MESSAGE
# ---------------------------------------------
def parse_pairs(text: str) -> list:
    tokens = text.upper().replace(",", " ").split()
    pairs  = [t for t in tokens if 3 <= len(t) <= 10]
    return pairs


# ---------------------------------------------
# TELEGRAM
# ---------------------------------------------
def send_message(chat_id, text):
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log.error(f"Send error: {e}")


def get_updates(offset=None):
    url    = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        resp = requests.get(url, params=params, timeout=35)
        return resp.json().get("result", [])
    except Exception as e:
        log.error(f"getUpdates error: {e}")
        return []


# ---------------------------------------------
# MAIN
# ---------------------------------------------
def main():
    log.info("FX Correlation Bot started. Listening for messages...")
    offset = None

    while True:
        updates = get_updates(offset)

        for update in updates:
            offset  = update["update_id"] + 1
            message = update.get("message", {})
            text    = message.get("text", "").strip()
            chat_id = message.get("chat", {}).get("id")

            if not text or not chat_id:
                continue

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