# Instagram → Discord Bot

Watches your own Instagram Professional account via the official Instagram Graph API and automatically posts new uploads to a Discord channel — photos as rich embeds, videos uploaded as native attachments so they play right in Discord. Runs on a schedule via GitHub Actions, so there's no server to maintain, and sends a failure alert to a separate channel if anything breaks (expired token, Discord outage, etc.).

## Features

- 🔄 Polls on a schedule (default every 15 min) via GitHub Actions — no always-on server required
- 🖼️ New photo posts show up as Discord embeds with image, caption, and link
- 🎥 New video posts are downloaded and re-uploaded as native Discord attachments (playable inline, not just a link)
- ⚠️ Sends a Discord alert to a dedicated channel if a run fails, so problems don't go unnoticed
- ✅ Includes a standalone test script to verify your setup without needing to publish a new Instagram post
- 🔒 Uses the official Instagram Graph API — no scraping, no ToS risk, works only with accounts you own/manage

## Requirements

- Instagram account converted to Professional (Business or Creator)
- That account linked to a Facebook Page you control
- A Meta App with Instagram Graph API access
- A Discord webhook (and optionally a second one for failure alerts)

## Quick start

See [SETUP.md](./SETUP.md) for the full walkthrough — getting Instagram Graph API credentials is the one genuinely fiddly part; everything else is copy/paste.

```bash
git clone <this-repo>
cd <this-repo>
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your real values
python3 test_setup.py  # verify everything's connected before going live
python3 main.py        # or deploy via GitHub Actions, see .github/workflows/
```

## Running continuously

Two options:
- **Locally / on your own server**: `python3 main.py` runs an infinite polling loop.
- **GitHub Actions** (recommended, no server needed): the included workflow at `.github/workflows/poll-instagram.yml` runs on a cron schedule. Add your credentials as repo secrets (`IG_USER_ID`, `IG_ACCESS_TOKEN`, `DISCORD_WEBHOOK_URL`, optionally `DISCORD_ALERT_WEBHOOK_URL`) and it handles the rest, including committing state between runs.

## License

Internal tool
The MIT License (MIT)

Copyright (c) 2026 Teck Liew

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
