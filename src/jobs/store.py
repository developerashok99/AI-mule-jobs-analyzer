from datetime import date

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


def save_postings(postings) -> int:
    """Upserts postings, keyed by dedupe_key so re-seeing the same job is a no-op.
    Returns count of genuinely new postings."""
    today = date.today().isoformat()
    jobs = get_db().jobs
    new_count = 0
    for job in postings:
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
                }
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            new_count += 1
    return new_count


def jobs_seen_on(day_iso: str):
    return list(get_db().jobs.find({"first_seen_date": day_iso}))


def all_jobs():
    return list(get_db().jobs.find({}))


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
