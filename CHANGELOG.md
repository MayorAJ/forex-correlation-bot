[1.1.0] - 2026-06-07
Changed

Replaced Yahoo Finance (yfinance) with the Frankfurter API for exchange rate data — more reliable coverage for minor forex pairs
Removed yfinance and pandas dependencies
Correlation is now calculated natively in pure Python — no external math libraries required

Added

python-dotenv support — bot token is now loaded from a .env file instead of being hardcoded in the script

[1.0.0] - Initial release
Added

Telegram bot that calculates pairwise correlation between 2–6 forex pairs
14-day lookback window using daily closes
Correlation strength labels (Very strong, Strong, Moderate, Weak, Very weak / none)
/start and /help commands