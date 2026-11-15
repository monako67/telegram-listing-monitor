# Telegram Listing Monitor

An asynchronous Telegram bot that watches server-rendered search pages and sends a message when new same-site links appear.

## Why it is useful

- Monitors several pages independently.
- Stores searches and already-seen links in SQLite.
- Does not spam old results after the first check.
- Supports allowlisted Telegram users and excluded words.
- Applies URL validation, response-size limits, timeouts and content-type checks.

## Quick start

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `BOT_TOKEN` in `.env`, then run:

```powershell
python bot.py
```

## Commands

- `/add name | https://site/search | excluded words`
- `/list`
- `/delete ID`

## Tests

```powershell
python -m pip install -r requirements-dev.txt
pytest -q
```

## Limitations

The generic extractor handles server-rendered HTML only. Pages requiring JavaScript, login or CAPTCHA need a site-specific adapter.

## Security

Never commit `.env`, bot tokens or a live SQLite database. Use `ALLOWED_USER_IDS` for private deployments.

