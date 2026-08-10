# AI MuleSoft Jobs Analyzer

Runs 3x/day, feeding a shared MongoDB (and a Telegram digest) that [mule-ai-frontend](https://github.com/developerashok99/mule-ai-frontend) reads from:

1. **Lecture → interview prep.** Pulls chapters from your [Notes](https://github.com/Ashokkumarkarri/Notes)
   repo and generates, per chapter: likely 3-5-yr-level interview questions + model answers, a condensed cheat
   sheet, and (for the DataWeave chapter specifically) practice transformation problems.
2. **Job-market intel.** Pulls MuleSoft postings from company ATS boards (Greenhouse/Lever/Workday) plus free
   aggregators (RemoteOK, Arbeitnow, optionally Adzuna), extracts salary where stated, scores each company
   (news-based + model judgment), tracks which skills/topics show up most often across real job descriptions, and
   prunes dead links from older postings.

## Why not just scrape LinkedIn/Naukri/Indeed directly

They all run active bot-detection (Naukri 406s on "recaptcha required" for anonymous requests, Indeed 403s plain
HTTP, LinkedIn's ToS bans automation outright). This repo does **not** do captcha-solving or IP/fingerprint
spoofing to defeat that - that's evading a security control, not scraping.

- `src/main.py` — runs 3x/day via GitHub Actions. Lecture Q&A/cheat sheets/DataWeave practice + company-board jobs
  (Greenhouse/Lever/Workday) + free aggregators + company scoring + stale-job pruning + JD skill-frequency report +
  Telegram digest. All of this hits plain public JSON APIs with no bot wall, safe to run from a cloud runner.
- `src/local_scrape.py` — LinkedIn/Naukri/Indeed, using Playwright with **your own logged-in browser session**.
  Must run on your own machine (residential IP), not CI - datacenter IPs get blocked far more aggressively. This
  still goes against those sites' ToS (risk to your account, go easy on how often you run it), and the CSS
  selectors it uses will need occasional fixing when those sites redesign their search pages.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in the keys below
```

- **Groq API key**: free at https://console.groq.com/keys. Note: the free tier has a **daily token cap**
  (100k tokens/day at time of writing). `src/groq_errors.py` detects this specific error (as opposed to a
  transient per-minute rate limit) and every generation loop stops cleanly the moment it's hit, rather than
  burning through the rest of a chapter list on doomed calls - whatever's left rolls to the next scheduled run
  (3x/day) automatically. Nothing is lost either way; the cache is keyed on chapter sha.
- **Telegram bot**: message @BotFather, `/newbot`, use a NEW bot (not one you use elsewhere) so this project's
  messages don't mix with anything else. Get your chat id by messaging the bot once, then hitting
  `https://api.telegram.org/bot<token>/getUpdates`.
- **MongoDB**: free M0 cluster at https://cloud.mongodb.com. Database Access → add a user (this gives you the
  username/password for the connection string, separate from your Atlas login). Network Access → allow
  `0.0.0.0/0`, since GitHub Actions runners (and Vercel, for the frontend) don't have a fixed IP - a
  single-IP-only allow list is a common cause of a TLS-handshake-looking connection failure that's actually just
  the IP being rejected. Copy the `mongodb+srv://...` connection string into `MONGODB_URI`.
- **Adzuna** (optional): free tier at https://developer.adzuna.com. Leave `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` blank
  to skip this source entirely - no error, it just contributes nothing.

### Run the daily pipeline manually

```bash
python -m src.main
```

### Add companies to track

Edit `src/jobs/sources/companies.json`. Every entry was individually verified live against the real
Greenhouse/Lever/Workday API before being added - big Indian IT-services firms (TCS/Infosys/Wipro/Cognizant/
Accenture/Capgemini) mostly don't run any of these three platforms under a guessable identifier, so don't guess;
verify with `src/jobs/discover_companies.py`:

```bash
python -m src.jobs.discover_companies greenhouse some-candidate-slug another-one
python -m src.jobs.discover_companies lever some-candidate-slug
python -m src.jobs.discover_companies workday tenant:wd1:SiteName
```

Finding candidate names in the first place still needs a search pass (not automated here) - this just automates
verifying each one before you trust it.

### LinkedIn / Naukri / Indeed (local only)

```bash
pip install playwright && playwright install chromium
python -m src.local_scrape login linkedin   # opens a real browser, log in by hand, press Enter when done
python -m src.local_scrape login naukri
python -m src.local_scrape login indeed
python -m src.local_scrape run
```

## GitHub Actions

`.github/workflows/daily.yml` runs `src/main.py` 3x/day. Add these as repo secrets (Settings → Secrets →
Actions): `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `MONGODB_URI`, and optionally
`ADZUNA_APP_ID`/`ADZUNA_APP_KEY`.

## What's not built yet

- Company reputation scoring only uses Google News headlines + the model's general knowledge (Glassdoor/
  AmbitionBox are both bot-walled the same way the job boards are). If you want ratings data in the mix, that'd
  need manual entry or a paid ratings API.
- `discover_companies.py` verifies candidates but doesn't find them - that half is still a manual/assisted search
  pass, not a cron job.
