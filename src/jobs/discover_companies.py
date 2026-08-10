"""Semi-automated company discovery: given a list of candidate slugs, checks all three
ATS platforms and reports which ones actually resolve and have current MuleSoft-related
postings. This is NOT part of the daily cron - finding candidate names in the first place
still needs a search pass (done manually/by an assistant periodically), but verifying
each one is fully scriptable and free, which is what this automates.

Usage:
    python -m src.jobs.discover_companies greenhouse slug1 slug2 slug3
    python -m src.jobs.discover_companies lever slug1 slug2
    python -m src.jobs.discover_companies workday tenant:wd:site tenant2:wd2:site2
"""
import sys

from src.jobs.sources.ats_boards import fetch_greenhouse, fetch_lever
from src.jobs.sources.workday import fetch_workday


def check_greenhouse(slugs):
    for slug in slugs:
        postings = fetch_greenhouse(slug)
        print(f"greenhouse/{slug}: {len(postings)} MuleSoft-matching posting(s)"
              + (" -> ADD to companies.json" if postings else ""))


def check_lever(slugs):
    for slug in slugs:
        postings = fetch_lever(slug)
        print(f"lever/{slug}: {len(postings)} MuleSoft-matching posting(s)"
              + (" -> ADD to companies.json" if postings else ""))


def check_workday(specs):
    for spec in specs:
        tenant, wd, site = spec.split(":")
        postings = fetch_workday(tenant, tenant, wd, site)
        print(f"workday/{tenant} ({wd}/{site}): {len(postings)} MuleSoft-matching posting(s)"
              + (" -> ADD to companies.json" if postings else ""))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return

    platform, candidates = sys.argv[1], sys.argv[2:]
    if platform == "greenhouse":
        check_greenhouse(candidates)
    elif platform == "lever":
        check_lever(candidates)
    elif platform == "workday":
        check_workday(candidates)
    else:
        print(f"unknown platform: {platform} (use greenhouse, lever, or workday)")


if __name__ == "__main__":
    main()
