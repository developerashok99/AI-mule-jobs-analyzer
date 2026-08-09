"""Aggregates skill/topic mentions across all collected job descriptions, so you know
what to prioritize in the remaining days of study."""
from collections import Counter

from src.jobs.skills_taxonomy import count_skills


def aggregate_skill_counts(job_rows) -> Counter:
    totals = Counter()
    for job in job_rows:
        text = f"{job.get('title', '')} {job.get('description', '')}"
        for skill, n in count_skills(text).items():
            totals[skill] += n
    return totals


def format_report(totals: Counter, job_count: int, top_n: int = 20) -> str:
    lines = [f"JD skill-frequency report ({job_count} job descriptions analyzed)\n"]
    for skill, count in totals.most_common(top_n):
        pct = round(100 * count / max(job_count, 1))
        lines.append(f"- {skill}: mentioned in ~{pct}% of postings ({count} mentions)")
    return "\n".join(lines)
