"""Checks whether tracked job URLs still resolve, and marks the ones that don't as
closed (soft-delete via a flag, not an actual removal, so history/salary-trend data
isn't lost). Only rechecks a capped batch per run (oldest-first) rather than every job
every day, since a full sweep of 70+ URLs daily isn't worth the request volume."""
import logging

import requests

from src.jobs import store

logger = logging.getLogger(__name__)

BATCH_SIZE = 25


def prune_stale_jobs():
    closed_count = 0
    for job in store.jobs_to_recheck(BATCH_SIZE):
        url = job.get("url")
        if not url:
            continue
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 405:  # some ATS boards reject HEAD, retry with GET
                resp = requests.get(url, timeout=10, allow_redirects=True)
            if resp.status_code in (404, 410):
                store.mark_job_closed(job["_id"])
                closed_count += 1
        except requests.RequestException:
            continue  # network hiccup isn't evidence the job closed, leave it alone
    return closed_count
