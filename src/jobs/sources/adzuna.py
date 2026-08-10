"""Adzuna is a real job aggregator (pulls from many boards, Indeed included indirectly)
with a genuine free tier - unlike the paid aggregator APIs (JSearch etc.) ruled out
earlier. Inactive until ADZUNA_APP_ID/ADZUNA_APP_KEY are set (free signup at
developer.adzuna.com) - fetch_all() just returns nothing until then, no error.
"""
import logging

import requests

from src.config import ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_COUNTRY
from .base import JobPosting
from ..salary_extraction import apply_salary

logger = logging.getLogger(__name__)

KEYWORDS = ["mulesoft", "mule esb", "anypoint"]

_COUNTRY_CURRENCY = {"in": "INR", "us": "USD", "gb": "GBP", "de": "EUR", "fr": "EUR"}


def fetch_all():
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    try:
        resp = requests.get(url, params={
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "what": "mulesoft",
            "results_per_page": 50,
        }, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Adzuna fetch failed")
        return []

    postings = []
    for job in resp.json().get("results", []):
        title = job.get("title", "")
        description = job.get("description", "")
        haystack = f"{title} {description}".lower()
        if not any(kw in haystack for kw in KEYWORDS):
            continue

        postings.append(apply_salary(JobPosting(
            source="adzuna",
            company=(job.get("company") or {}).get("display_name", ""),
            title=title,
            location=(job.get("location") or {}).get("display_name", ""),
            url=job.get("redirect_url", ""),
            description=description,
            external_id=str(job.get("id", "")),
            posted_date=job.get("created", ""),
            salary_min=int(job.get("salary_min") or 0),
            salary_max=int(job.get("salary_max") or 0),
            salary_currency=_COUNTRY_CURRENCY.get(ADZUNA_COUNTRY, "") if job.get("salary_min") else "",
        )))
    return postings
