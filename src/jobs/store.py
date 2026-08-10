import re
from datetime import date, datetime, timedelta

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from src.config import MONGODB_URI, MONGODB_DB_NAME

_client = None


def get_db():
    global _client
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set (see .env.example)")
    if _client is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        try:
            _client.admin.command("ping")
        except ConnectionFailure as exc:
            raise RuntimeError(
                "Could not reach MongoDB - check MONGODB_URI, and that your Atlas "
                "cluster's Network Access allows connections from this machine "
                "(0.0.0.0/0 if this runs in GitHub Actions, whose IPs vary)."
            ) from exc
    return _client[MONGODB_DB_NAME]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _signature(company: str, title: str) -> str:
    return f"{_normalize(company)}:{_normalize(title)}"


def save_postings(postings) -> int:
    """Upserts postings, keyed by dedupe_key so re-seeing the same job is a no-op.
    Also skips jobs that are the same role at the same company under a DIFFERENT
    source (e.g. a company's own board and RemoteOK both listing it) via a normalized
    company+title signature. Returns count of genuinely new postings."""
    today = date.today().isoformat()
    jobs = get_db().jobs
    new_count = 0
    for job in postings:
        dedupe_key = job.dedupe_key()
        signature = _signature(job.company, job.title)

        if not jobs.find_one({"_id": dedupe_key}, {"_id": 1}):
            # genuinely new dedupe_key - but skip it if the same role is already
            # tracked under a different source (e.g. a company's own board + RemoteOK)
            existing = jobs.find_one({"signature": signature}, {"_id": 1})
            if existing:
                continue

        result = jobs.update_one(
            {"_id": job.dedupe_key()},
            {
                "$setOnInsert": {
                    "source": job.source,
                    "company": job.company,
                    "title": job.title,
                    "location": job.location,
                    "url": job.url,
                    "description": job.description,
                    "posted_date": job.posted_date,
                    "first_seen_date": today,
                    "signature": signature,
                    "closed": False,
                }
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            new_count += 1
        else:
            # backfills signature/closed onto jobs seen before these fields existed -
            # safe to recompute every time since company/title never change post-insert
            jobs.update_one(
                {"_id": dedupe_key, "signature": {"$exists": False}},
                {"$set": {"signature": signature, "closed": False}},
            )

        if job.salary_min:
            # backfills salary onto jobs seen before salary extraction existed, and
            # refreshes it if a re-fetch finds a better match - doesn't touch the
            # $setOnInsert fields above, which stay fixed at first-seen values
            jobs.update_one(
                {"_id": job.dedupe_key()},
                {"$set": {
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "salary_currency": job.salary_currency,
                    "salary_text": job.salary_text,
                }},
            )
    return new_count


def jobs_seen_on(day_iso: str):
    return list(get_db().jobs.find({"first_seen_date": day_iso}))


def all_jobs():
    return list(get_db().jobs.find({"closed": {"$ne": True}}))


def jobs_to_recheck(limit: int = 25):
    """Oldest not-yet-closed jobs, for the daily stale-link check to rotate through
    without re-checking all of them (and all their URLs) every single run."""
    return list(
        get_db().jobs.find({"closed": {"$ne": True}})
        .sort("first_seen_date", 1)
        .limit(limit)
    )


def mark_job_closed(dedupe_key: str):
    get_db().jobs.update_one(
        {"_id": dedupe_key},
        {"$set": {"closed": True, "closed_date": date.today().isoformat()}},
    )


def is_company_recently_scored(company: str, max_age_days: int = 14) -> bool:
    doc = get_db().companies.find_one({"_id": company})
    if not doc:
        return False
    scored = datetime.fromisoformat(doc["scored_date"])
    return (datetime.now() - scored) < timedelta(days=max_age_days)


def save_company_verdict(company: str, score: int, verdict: str):
    get_db().companies.update_one(
        {"_id": company},
        {"$set": {"score": score, "verdict": verdict, "scored_date": date.today().isoformat()}},
        upsert=True,
    )


def save_keyword_counts(run_date: str, counts: dict):
    get_db().jd_reports.update_one(
        {"_id": run_date},
        {"$set": {"counts": counts}},
        upsert=True,
    )
