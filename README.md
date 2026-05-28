# Daily Digest NewsBot

A personal news digest bot that posts a tightly-edited Telegram briefing twice a day, plus a separate breaking-news alerter that wakes you up only when something genuinely big happens.

## What it does

- **Morning brief** at ~06:00 IST and **evening brief** at ~18:00 IST, delivered to a Telegram chat of your choice.
- Each brief opens with a Delhi weather line and a market snapshot (Nifty, Sensex, USD/INR, BTC), then categorised stories: Geopolitics · AI & Tech · AI Releases · India Business · India News · Science & Space.
- A **Breaking News** workflow runs every 2 hours and pushes a one-off Telegram alert only when something matches a strict criteria list (war escalation, head-of-state event, 3%+ market crash, major AI model release, large-scale disaster, etc.). Deduplicated so the same alert never fires twice within 24 hours.
- Every story is filtered through a Groq-hosted LLaMA 3.3-70B with a strict system prompt that bans filler language and demands a WHAT / SO WHAT / NEXT structure.

## Tech stack

- Python 3.11
- `feedparser` for RSS
- **Groq + LLaMA 3.3-70B** for summarisation (free tier)
- `python-telegram-bot` for delivery
- `requests` for the weather/markets sidebars
- **GitHub Actions** runs the workflows
- **cron-job.org** triggers the daily briefs via GitHub's `repository_dispatch` API for sub-minute punctuality (the breaking-news workflow uses GitHub's native cron, where ~15 min drift is fine)

## RSS sources

| Category | Feeds |
|---|---|
| Geopolitics | SCMP, Reuters World (Google News mirror), BBC, Al Jazeera, Google News Geopolitics |
| AI & Tech | TechCrunch AI, The Verge AI, Google News AI |
| AI Releases | OpenAI Blog, Anthropic News, Google DeepMind, Meta AI, Mistral AI, Google AI Blog, VentureBeat AI |
| India Business | Inc42, Entrackr, YourStory, VCCircle, The Ken, two Google News startup queries |
| India News | Times of India Top Stories, The Hindu National, Indian Express India, Google News India National |
| Science & Space | Google News Science |
| Breaking (separate workflow) | BBC, Reuters via Google News, Al Jazeera, Google News Breaking |

## Setup

### 1. Fork

Fork this repo to your own GitHub account.

### 2. Create accounts and tokens

- **Groq** — sign up at https://console.groq.com → Create API key (`gsk_...`).
- **Telegram bot** — chat with `@BotFather` → `/newbot` → copy the bot token. Then send any message to the bot from your account and fetch your chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`.
- **GitHub PAT** for cron-job.org — https://github.com/settings/tokens?type=beta → fine-grained PAT scoped to the forked repo, with **Contents: Read and write**.

### 3. GitHub Actions secrets

In the forked repo: **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Name | Value |
|---|---|
| `GROQ_API_KEY` | your Groq key |
| `TELEGRAM_BOT_TOKEN` | your bot token |
| `TELEGRAM_CHAT_ID` | your numeric chat ID |

### 4. cron-job.org

Sign up at https://cron-job.org (free, no card). Create two cron jobs:

| Job | UTC schedule | IST equivalent | JSON body |
|---|---|---|---|
| Morning | `00:30` daily | 06:00 IST | `{"event_type": "morning_digest"}` |
| Evening | `12:30` daily | 18:00 IST | `{"event_type": "evening_digest"}` |

Both jobs use the same setup:

- **URL**: `https://api.github.com/repos/<YOUR_USER>/daily-digest-newsbot/dispatches`
- **Method**: `POST`
- **Headers**:
  - `Authorization: Bearer <YOUR_GITHUB_PAT>`
  - `Accept: application/vnd.github+json`
- **Body**: JSON, as above.

cron-job.org → "Run now" on each to test. Within ~10 seconds an Actions run appears in your repo and a brief lands on Telegram.

### 5. Breaking news workflow

`.github/workflows/breaking.yml` is already configured to run every 2 hours on GitHub's native cron — no extra setup once the secrets above are in place.

### 6. Local development

```bash
cp .env.example .env  # then fill in your keys
pip install -r requirements.txt
python bot.py --run-now morning   # one-shot test
python breaking.py                 # test the alerter
```

## Screenshots

> _Telegram screenshots: morning brief, breaking alert. Add `.png`s to `/docs/` and reference them here._

## Project layout

```
bot.py              # daily digest entrypoint
breaking.py         # breaking-news alerter
fetcher.py          # RSS fetch + 12h filter
summarizer.py       # Groq call for the daily brief
weather.py          # Open-Meteo Delhi weather
markets.py          # Yahoo Finance + ExchangeRate + CoinGecko snapshot
telegram_sender.py  # Telegram delivery + HTML formatting
config.py           # env vars, RSS feed list, system prompt
.github/workflows/
  digest.yml        # repository_dispatch (cron-job.org) + workflow_dispatch
  breaking.yml      # every-2-hours GitHub cron
```

## License

MIT. See [LICENSE](LICENSE).
