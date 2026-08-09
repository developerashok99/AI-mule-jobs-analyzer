import os
import sqlite3
from contextlib import contextmanager
from datetime import date

from src.config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    dedupe_key TEXT PRIMARY KEY,
    source TEXT,
    company TEXT,
    title TEXT,
    location TEXT,
    url TEXT,
    description TEXT,
    posted_date TEXT,
    first_seen_date TEXT,
    experience_min INTEGER,
    experience_max INTEGER,
    company_score INTEGER,
    company_verdict TEXT
);

CREATE TABLE IF NOT EXISTS jd_keyword_counts (
    run_date TEXT,
    keyword TEXT,
    count INTEGER,
    PRIMARY KEY (run_date, keyword)
);
"""


@contextmanager
def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_postings(postings) -> int:
    """Inserts new postings, skips ones already seen (by dedupe_key). Returns count of new rows."""
    today = date.today().isoformat()
    new_count = 0
    with connect() as conn:
        for job in postings:
            cur = conn.execute(
                "INSERT OR IGNORE INTO jobs "
                "(dedupe_key, source, company, title, location, url, description, posted_date, first_seen_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job.dedupe_key(), job.source, job.company, job.title, job.location,
                 job.url, job.description, job.posted_date, today),
            )
            if cur.rowcount:
                new_count += 1
    return new_count


def jobs_seen_on(day_iso: str):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs WHERE first_seen_date = ?", (day_iso,)).fetchall()
        return [dict(r) for r in rows]


def all_jobs():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs").fetchall()
        return [dict(r) for r in rows]


def save_company_verdict(company: str, score: int, verdict: str):
    with connect() as conn:
        conn.execute(
            "UPDATE jobs SET company_score = ?, company_verdict = ? WHERE company = ?",
            (score, verdict, company),
        )


def save_keyword_counts(run_date: str, counts: dict):
    with connect() as conn:
        for keyword, count in counts.items():
            conn.execute(
                "INSERT OR REPLACE INTO jd_keyword_counts (run_date, keyword, count) VALUES (?, ?, ?)",
                (run_date, keyword, count),
            )
