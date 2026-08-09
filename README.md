# AI MuleSoft Jobs Analyzer

Two things, running on a daily cadence, feeding a Telegram bot:

1. **Lecture → interview questions.** Pulls chapters from your [Notes](https://github.com/Ashokkumarkarri/Notes)
   repo and generates likely 3-5-yr-level interview questions + model answers per chapter, so you get quizzed
   right after finishing each topic.
2. **Job-market intel.** Pulls MuleSoft postings from company ATS boards, scores each company (pay/stability
   signal from recent news + the model's own knowledge), and tracks which skills/topics show up most often across
   real job descriptions - so you know what to prioritize while you still have study time left.

## Why two separate pipelines

LinkedIn / Naukri / Indeed all run active bot-detection (Naukri 406s on "recaptcha required" for anonymous
requests, Indeed 403s plain HTTP, LinkedIn's ToS bans automation outright). This repo does **not** do
captcha-solving or IP/fingerprint spoofing to defeat that - that's evading a security control, not scraping.

- `src/main.py` — runs daily via GitHub Actions. Lecture Q&A + company-board (Greenhouse/Lever) jobs + company
  scoring + JD skill-frequency report + Telegram digest. All of this hits plain public JSON APIs with no bot wall,
  safe to run from a cloud runner.
- `src/local_scrape.py` — LinkedIn/Naukri/Indeed, using Playwright with **your own logged-in browser session**.
  Must run on your own machine (residential IP), not CI - datacenter IPs get blocked far more aggressively. This
  still goes against those sites' ToS (risk to your account, go easy on how often you run it), and the CSS
  selectors it uses will need occasional fixing when those sites redesign their search pages.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

- **Groq API key**: free at https://console.groq.com/keys
- **Telegram bot**: message @BotFather, `/newbot`, use a NEW bot (not one you use elsewhere) so this project's
  messages don't mix with anything else. Get your chat id by messaging the bot once, then hitting
  `https://api.telegram.org/bot<token>/getUpdates`.

### Run the daily pipeline manually

```bash
python -m src.main
```

### Add companies to track

Edit `src/jobs/sources/companies.json`. It ships **empty** on purpose — big Indian IT-services firms
(TCS/Infosys/Wipro/Cognizant/Accenture/Capgemini) mostly don't run Greenhouse or Lever, so slugs can't be
guessed. Check a company's careers page: if the URL contains `greenhouse.io` or `jobs.lever.co`, copy the slug
into the matching list.

### LinkedIn / Naukri / Indeed (local only)

```bash
pip install playwright && playwright install chromium
python -m src.local_scrape login linkedin   # opens a real browser, log in by hand, press Enter when done
python -m src.local_scrape login naukri
python -m src.local_scrape login indeed
python -m src.local_scrape run
```

## GitHub Actions

`.github/workflows/daily.yml` runs `src/main.py` daily. Add these as repo secrets (Settings → Secrets → Actions):
`GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## What's not built yet

- Skill-gap dashboard, resume/JD matcher, application tracker, mock-interview chat mode — flagged as future
  additions, not started.
- Company scoring only uses Google News headlines + the model's general knowledge (Glassdoor/AmbitionBox are
  both bot-walled the same way the job boards are). If you want ratings data in the mix, that'd need manual entry
  or a paid ratings API.
