"""Best-effort scrapers for LinkedIn / Naukri / Indeed using a real logged-in browser
session (Playwright), run LOCALLY on your own machine — not from GitHub Actions.

Why local-only: these three sites run active bot-detection (Naukri returns
"406 recaptcha required" on anonymous API calls; Indeed 403s plain requests; LinkedIn's
ToS bans automation outright). Datacenter IPs (including GitHub Actions runners) get
blocked far more aggressively than residential ones, and this project intentionally does
NOT do captcha-solving or IP/fingerprint spoofing to get around that — that's evading a
security control, not scraping. What this DOES do is automate a real Chromium browser
using YOUR OWN logged-in session (you log in once by hand, the session is reused), which
is the same access a human doing manual job search has. That still breaks these sites'
ToS (you accepted that risk) and can get YOUR account rate-limited or restricted — go
slow, don't run this many times a day.

Setup:
    pip install playwright && playwright install chromium
    python -m src.local_scrape login linkedin   # opens a real browser window, log in by hand, close it
    python -m src.local_scrape login naukri
    python -m src.local_scrape login indeed
    python -m src.local_scrape run               # scrapes all three using the saved sessions

Selectors below match each site's layout as of when this was written and WILL break when
the sites redesign their search pages — that's normal for scraping, not a bug. If a run
returns zero results, the first thing to check is whether the CSS selectors still match.
"""
import logging
import os
import random
import time

from src.config import DATA_DIR, TARGET_EXPERIENCE_MIN, TARGET_EXPERIENCE_MAX
from .base import JobPosting

logger = logging.getLogger(__name__)

SESSION_DIR = os.path.join(DATA_DIR, "browser_sessions")
SEARCH_KEYWORD = "mulesoft developer"


def _session_path(site: str) -> str:
    os.makedirs(SESSION_DIR, exist_ok=True)
    return os.path.join(SESSION_DIR, f"{site}.json")


def _human_pause(a=1.5, b=4.0):
    time.sleep(random.uniform(a, b))


def interactive_login(site: str):
    """Opens a real, visible browser window so you can log in by hand, then saves the
    session (cookies/local storage) to disk so future runs don't need to log in again."""
    from playwright.sync_api import sync_playwright

    urls = {
        "linkedin": "https://www.linkedin.com/login",
        "naukri": "https://www.naukri.com/nlogin/login",
        "indeed": "https://secure.indeed.com/account/login",
    }
    if site not in urls:
        raise ValueError(f"unknown site: {site}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(urls[site])
        input(f"Log in to {site} in the opened browser window, then press Enter here to save the session...")
        context.storage_state(path=_session_path(site))
        browser.close()
    logger.info("Saved %s session to %s", site, _session_path(site))


def _scrape_with_session(site: str, scrape_fn):
    from playwright.sync_api import sync_playwright

    session_path = _session_path(site)
    if not os.path.exists(session_path):
        logger.warning("No saved session for %s — run `python -m src.local_scrape login %s` first", site, site)
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session_path)
        page = context.new_page()
        try:
            postings = scrape_fn(page)
        except Exception:
            logger.exception("%s scrape failed", site)
            postings = []
        finally:
            browser.close()
    return postings


def _scrape_linkedin(page):
    postings = []
    exp_filter = f"f_E=3%2C4"  # LinkedIn's "Associate" + "Mid-Senior level" facets, closest match to 3-5 yrs
    url = f"https://www.linkedin.com/jobs/search/?keywords={SEARCH_KEYWORD.replace(' ', '%20')}&{exp_filter}"
    page.goto(url)
    _human_pause()

    for _ in range(5):  # scroll to load more results, LinkedIn lazy-loads the list
        page.mouse.wheel(0, 2000)
        _human_pause(1.0, 2.5)

    cards = page.query_selector_all("div.job-search-card")
    for card in cards:
        title_el = card.query_selector("h3.base-search-card__title")
        company_el = card.query_selector("h4.base-search-card__subtitle")
        location_el = card.query_selector("span.job-search-card__location")
        link_el = card.query_selector("a.base-card__full-link")
        if not (title_el and link_el):
            continue
        postings.append(JobPosting(
            source="linkedin",
            company=company_el.inner_text().strip() if company_el else "",
            title=title_el.inner_text().strip(),
            location=location_el.inner_text().strip() if location_el else "",
            url=link_el.get_attribute("href") or "",
            description="",  # full JD needs a follow-up page visit; kept out for now to reduce request volume
        ))
    return postings


def _scrape_naukri(page):
    postings = []
    url = f"https://www.naukri.com/{SEARCH_KEYWORD.replace(' ', '-')}-jobs-{TARGET_EXPERIENCE_MIN}-to-{TARGET_EXPERIENCE_MAX}-years"
    page.goto(url)
    _human_pause()

    cards = page.query_selector_all("div.cust-job-tuple")
    for card in cards:
        title_el = card.query_selector("a.title")
        company_el = card.query_selector("a.comp-name")
        location_el = card.query_selector("span.locWdth")
        if not title_el:
            continue
        postings.append(JobPosting(
            source="naukri",
            company=company_el.inner_text().strip() if company_el else "",
            title=title_el.inner_text().strip(),
            location=location_el.inner_text().strip() if location_el else "",
            url=title_el.get_attribute("href") or "",
            description="",
        ))
    return postings


def _scrape_indeed(page):
    postings = []
    url = f"https://www.indeed.com/jobs?q={SEARCH_KEYWORD.replace(' ', '+')}&explvl=mid_level"
    page.goto(url)
    _human_pause()

    cards = page.query_selector_all("div.job_seen_beacon")
    for card in cards:
        title_el = card.query_selector("h2.jobTitle span")
        company_el = card.query_selector("span.companyName")
        location_el = card.query_selector("div.companyLocation")
        link_el = card.query_selector("a")
        if not title_el:
            continue
        postings.append(JobPosting(
            source="indeed",
            company=company_el.inner_text().strip() if company_el else "",
            title=title_el.inner_text().strip(),
            location=location_el.inner_text().strip() if location_el else "",
            url="https://www.indeed.com" + (link_el.get_attribute("href") or "") if link_el else "",
            description="",
        ))
    return postings


def fetch_linkedin():
    return _scrape_with_session("linkedin", _scrape_linkedin)


def fetch_naukri():
    return _scrape_with_session("naukri", _scrape_naukri)


def fetch_indeed():
    return _scrape_with_session("indeed", _scrape_indeed)
