"""Scrapes public, unauthenticated ATS job-board APIs (Greenhouse, Lever).

These are meant to be read by external sites (they back the "jobs" widget companies
embed on their own careers pages), so unlike Naukri/Indeed/LinkedIn they have no
captcha/bot-wall and are safe to call on a schedule from CI. Coverage is limited to
whichever companies you add to companies.json under their real board slug. See
workday.py for the third source - most large enterprises use Workday rather than
Greenhouse/Lever, so that's where most of the MNC-scale coverage comes from.
"""
import json
import logging
import os

import requests

from .base import JobPosting
from .workday import fetch_workday
from ..salary_extraction import apply_salary

logger = logging.getLogger(__name__)

COMPANIES_PATH = os.path.join(os.path.dirname(__file__), "companies.json")
KEYWORDS = ["mulesoft", "mule esb", "anypoint"]


def _load_companies():
    with open(COMPANIES_PATH) as f:
        return json.load(f)


def _matches_mulesoft(title: str, description: str) -> bool:
    haystack = f"{title} {description}".lower()
    return any(kw in haystack for kw in KEYWORDS)


def fetch_greenhouse(slug: str):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Greenhouse fetch failed for %s", slug)
        return []

    postings = []
    for job in resp.json().get("jobs", []):
        description = job.get("content", "")
        if not _matches_mulesoft(job["title"], description):
            continue
        postings.append(JobPosting(
            source="greenhouse",
            company=slug,
            title=job["title"],
            location=(job.get("location") or {}).get("name", ""),
            url=job.get("absolute_url", ""),
            description=description,
            external_id=str(job.get("id", "")),
            posted_date=job.get("updated_at", ""),
        ))
    return postings


def fetch_lever(slug: str):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Lever fetch failed for %s", slug)
        return []

    postings = []
    for job in resp.json():
        description = job.get("descriptionPlain", "") or job.get("description", "")
        if not _matches_mulesoft(job.get("text", ""), description):
            continue
        postings.append(JobPosting(
            source="lever",
            company=slug,
            title=job.get("text", ""),
            location=(job.get("categories") or {}).get("location", ""),
            url=job.get("hostedUrl", ""),
            description=description,
            external_id=job.get("id", ""),
            posted_date=str(job.get("createdAt", "")),
        ))
    return postings


def fetch_all():
    companies = _load_companies()
    postings = []
    for slug in companies.get("greenhouse", []):
        postings.extend(fetch_greenhouse(slug))
    for slug in companies.get("lever", []):
        postings.extend(fetch_lever(slug))
    for entry in companies.get("workday", []):
        postings.extend(fetch_workday(entry["company"], entry["tenant"], entry["wd"], entry["site"]))
    return [apply_salary(p) for p in postings]
