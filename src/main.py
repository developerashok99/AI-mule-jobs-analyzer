"""Daily pipeline entry point, meant to run in GitHub Actions:
1. Generate interview Q&A for any new/changed lecture chapters
2. Pull MuleSoft postings from configured ATS company boards
3. Score any newly-seen companies
4. Update the JD skill-frequency report
5. Send a Telegram digest

Does NOT run the LinkedIn/Naukri/Indeed scrapers - those need a real browser session and
should run locally (see src/local_scrape.py and src/jobs/sources/browser_boards.py).
"""
import logging
from datetime import date

from src.delivery import telegram_bot
from src.jobs import jd_analysis, store
from src.jobs.company_score import score_company
from src.jobs.sources import ats_boards
from src.lecture_qna import runner as lecture_runner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run():
    today = date.today().isoformat()
    sections = [f"MuleSoft job-hunt daily digest - {today}"]

    updated_chapters = lecture_runner.run()
    if updated_chapters:
        sections.append(f"\nNew interview Q&A generated for: {', '.join(updated_chapters)}")

    postings = ats_boards.fetch_all()
    new_count = store.save_postings(postings)
    sections.append(f"\nJobs: {len(postings)} MuleSoft postings found today, {new_count} new.")

    new_jobs_today = store.jobs_seen_on(today)
    companies_scored = set()
    for job in new_jobs_today:
        company = job["company"]
        if company in companies_scored:
            continue
        companies_scored.add(company)
        score, verdict = score_company(company)
        if score is not None:
            store.save_company_verdict(company, score, verdict)
            sections.append(f"\n{company}: {score}/10 - {verdict}")

    all_jobs = store.all_jobs()
    totals = jd_analysis.aggregate_skill_counts(all_jobs)
    if totals:
        sections.append("\n" + jd_analysis.format_report(totals, len(all_jobs), top_n=10))

    digest = "\n".join(sections)
    logger.info(digest)
    telegram_bot.send_message(digest)


if __name__ == "__main__":
    run()
