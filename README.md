# FX Correlation Bot

A Telegram bot that calculates pairwise correlation between two or more forex pairs based on the last 14 days of daily closing prices.

## Usage

Send two or more forex pair symbols to the bot in Telegram, space or comma separated:

  EURUSD GBPUSD NZDCHF

The bot returns the correlation coefficient and a strength label (Very strong, Strong, Moderate, Weak, Very weak) for each pair combination.

## Rules

- Minimum 2 pairs, maximum 6 pairs per request
- Pair names must be standard 6-character forex symbols (e.g. EURUSD, GBPJPY)
- Data is sourced from the [Frankfurter API](https://frankfurter.dev) — free, no API key required
- Correlation is calculated on daily closes, lookback window is 14 days

## Correlation Scale

  +0.85 to +1.00 — Very strong positive
  +0.65 to +0.84 — Strong positive
  +0.40 to +0.64 — Moderate positive
  +0.20 to +0.39 — Weak positive
   0.00 to +0.19 — Very weak / none
  Negative values — Same scale, opposite direction

## Setup

1. `pip install requests python-dotenv`
2. Create a `.env` file in the project folder and add your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   ```
3. `python3 fx_correlation_bot.py`

## Commands

  /start or /help — Show usage instructions

## Try it
[@FX_C_C_bot](https://t.me/FX_C_C_bot)

## Version
1.1.0
