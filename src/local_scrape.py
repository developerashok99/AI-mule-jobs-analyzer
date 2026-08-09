"""Entry point for the LinkedIn/Naukri/Indeed scrapers. Run this LOCALLY on your own
machine (not in CI) — see the module docstring in src/jobs/sources/browser_boards.py
for why. Requires: pip install playwright && playwright install chromium
"""
import logging
import sys

from src.jobs import store
from src.jobs.sources import browser_boards

logging.basicConfig(level=logging.INFO)


def main():
    if len(sys.argv) < 2:
        print("usage:\n"
              "  python -m src.local_scrape login <linkedin|naukri|indeed>\n"
              "  python -m src.local_scrape run")
        return

    command = sys.argv[1]
    if command == "login":
        site = sys.argv[2]
        browser_boards.interactive_login(site)
        return

    if command == "run":
        all_postings = (
            browser_boards.fetch_linkedin()
            + browser_boards.fetch_naukri()
            + browser_boards.fetch_indeed()
        )
        new_count = store.save_postings(all_postings)
        print(f"Fetched {len(all_postings)} postings, {new_count} new.")
        return

    print(f"unknown command: {command}")


if __name__ == "__main__":
    main()
