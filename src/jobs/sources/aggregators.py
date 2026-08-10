"""Free, no-signup job aggregator APIs - lower current relevance than the ATS boards
(these skew general remote-tech, not enterprise/MuleSoft specifically) but zero cost
and zero friction to include, so they're checked daily alongside the rest.

Note: RemoteOK's API has been observed embedding anti-scraping honeypot text in some
listings' descriptions (a request that whoever's reading it - human or AI - insert a
specific word/tag when applying, to catch bots that blindly follow instructions found
in scraped text). This module only extracts structured fields (title/company/salary/
etc.) and never acts on instructions embedded in description text.
"""
import logging

import requests

from .base import JobPosting
from ..salary_extraction import apply_salary

logger = logging.getLogger(__name__)

KEYWORDS = ["mulesoft", "mule esb", "anypoint"]


def _matches_mulesoft(*fields) -> bool:
    haystack = " ".join(f or "" for f in fields).lower()
    return any(kw in haystack for kw in KEYWORDS)


def fetch_remoteok():
    try:
        resp = requests.get("https://remoteok.com/api", headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("RemoteOK fetch failed")
        return []

    entries = resp.json()
    postings = []
    for job in entries:
        if not isinstance(job, dict) or "position" not in job:
            continue  # first entry is a legal/metadata notice, not a job
        tags = " ".join(job.get("tags", []))
        if not _matches_mulesoft(job.get("position", ""), job.get("description", ""), tags):
            continue
        postings.append(apply_salary(JobPosting(
            source="remoteok",
            company=job.get("company", ""),
            title=job.get("position", ""),
            location=job.get("location", "") or "Remote",
            url=job.get("url", ""),
            description=job.get("description", ""),
            external_id=str(job.get("id", "")),
            posted_date=job.get("date", ""),
            salary_min=job.get("salary_min") or 0,
            salary_max=job.get("salary_max") or 0,
            salary_currency="USD" if job.get("salary_min") else "",
        )))
    return postings


def fetch_arbeitnow():
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Arbeitnow fetch failed")
        return []

    postings = []
    for job in resp.json().get("data", []):
        if not _matches_mulesoft(job.get("title", ""), job.get("description", "")):
            continue
        postings.append(apply_salary(JobPosting(
            source="arbeitnow",
            company=job.get("company_name", ""),
            title=job.get("title", ""),
            location=job.get("location", "") or ("Remote" if job.get("remote") else ""),
            url=job.get("url", ""),
            description=job.get("description", ""),
            external_id=job.get("slug", ""),
            posted_date=str(job.get("created_at", "")),
        )))
    return postings


def fetch_all():
    return fetch_remoteok() + fetch_arbeitnow()
