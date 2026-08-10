"""Scrapes Workday-hosted career sites via their own search/detail JSON API.

Workday is the ATS most large enterprises (and the big MuleSoft-hiring MNCs
specifically) actually use - unlike Greenhouse/Lever, which skew toward
startups/mid-size tech. Each Workday tenant needs three values (tenant, wd host
number, site name) that vary per company and can't be guessed reliably - they
come from a real job URL, e.g.
https://amgen.wd1.myworkdayjobs.com/en-US/Careers/job/... -> tenant=amgen, wd=wd1, site=Careers.

Unlike Greenhouse/Lever this API supports real server-side search, so we query it
directly with each keyword instead of pulling every job and filtering client-side -
some Workday boards have thousands of postings.
"""
import logging
import time

import requests

from .base import JobPosting

logger = logging.getLogger(__name__)

KEYWORDS = ["mulesoft", "anypoint"]
MAX_ATTEMPTS = 3


def _request_with_retry(method: str, url: str, **kwargs):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.request(method, url, timeout=20, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(2 * attempt)  # Workday tenants have been flaky under bursty traffic


def fetch_workday(company: str, tenant: str, wd: str, site: str):
    base = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    postings = []
    seen_paths = set()

    for keyword in KEYWORDS:
        try:
            resp = _request_with_retry(
                "POST",
                f"{base}/jobs",
                json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": keyword},
                headers={"Accept": "application/json"},
            )
        except requests.RequestException:
            logger.exception("Workday search failed for %s (%s)", company, keyword)
            continue

        for job in resp.json().get("jobPostings", []):
            path = job.get("externalPath", "")
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)

            description, url = _fetch_detail(base, path)
            postings.append(JobPosting(
                source="workday",
                company=company,
                title=job.get("title", ""),
                location=job.get("locationsText", ""),
                url=url or f"{base}{path}",
                description=description,
                external_id=path,
                posted_date=job.get("postedOn", ""),
            ))

    return postings


def _fetch_detail(base: str, path: str):
    try:
        resp = _request_with_retry("GET", f"{base}{path}", headers={"Accept": "application/json"})
    except requests.RequestException:
        logger.exception("Workday job detail fetch failed for %s%s", base, path)
        return "", ""

    info = resp.json().get("jobPostingInfo", {})
    return info.get("jobDescription", ""), info.get("externalUrl", "")
