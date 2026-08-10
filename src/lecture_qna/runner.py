"""Walks every lecture chapter and generates interview Q&A + a cheat sheet for
new/changed chapters only. Results and the per-chapter cache (by GitHub blob sha) both
live in MongoDB, so nothing needs to be committed back to the repo from CI.

Stops early (rather than burning through 20 more doomed calls) the moment Groq's daily
token cap is hit - whatever's left over just rolls to the next scheduled run (3x/day),
so a single run never needs to cover all 23 chapters' worth of generation by itself.
"""
import logging
from datetime import date

from src.groq_errors import GroqQuotaExhausted
from src.jobs.store import get_db
from src.lecture_qna.cheat_sheet import generate_cheat_sheet
from src.lecture_qna.dataweave_practice import generate_practice_problems
from src.lecture_qna.fetch_notes import list_chapters, fetch_chapter_text
from src.lecture_qna.generate_questions import generate_questions_for_chapter
from src.lecture_qna.question_parser import parse_questions

logger = logging.getLogger(__name__)

DATAWEAVE_CHAPTER = "07 - DataWeave and Transform Message.md"


def _backfill_missing_fields(collection, name, cached):
    updates = {}
    if "questions" not in cached:
        # pure parsing of already-generated markdown, no LLM call needed
        updates["questions"] = parse_questions(name, cached["questions_markdown"])
    if updates:
        collection.update_one({"_id": name}, {"$set": updates})


def run():
    collection = get_db().lecture_qna
    chapters = list_chapters()

    new_or_changed = []
    quota_exhausted = False
    for chapter in chapters:
        if quota_exhausted:
            break

        name, sha = chapter["name"], chapter["sha"]
        cached = collection.find_one({"_id": name})

        if cached and cached.get("sha") == sha:
            _backfill_missing_fields(collection, name, cached)
            if "cheat_sheet_markdown" not in cached:
                text = fetch_chapter_text(chapter["download_url"])
                try:
                    sheet = generate_cheat_sheet(name, text)
                except GroqQuotaExhausted:
                    logger.info("Groq daily quota reached - stopping here, rest picks up next run")
                    quota_exhausted = True
                    continue
                if sheet:
                    collection.update_one(
                        {"_id": name},
                        {"$set": {"cheat_sheet_markdown": sheet, "generated_date": date.today().isoformat()}},
                    )
            continue  # already generated for this exact version of the chapter

        logger.info("Generating interview questions for: %s", name)
        text = fetch_chapter_text(chapter["download_url"])
        try:
            qa_markdown = generate_questions_for_chapter(name, text)
        except GroqQuotaExhausted:
            logger.info("Groq daily quota reached - stopping here, rest picks up next run")
            quota_exhausted = True
            continue
        if not qa_markdown:
            continue  # LLM call failed for a non-quota reason, leave cache untouched to retry next run

        try:
            cheat_sheet = generate_cheat_sheet(name, text)
        except GroqQuotaExhausted:
            cheat_sheet = ""  # got the Q&A at least - cheat sheet backfills next run

        collection.update_one(
            {"_id": name},
            {"$set": {
                "sha": sha,
                "questions_markdown": qa_markdown,
                "questions": parse_questions(name, qa_markdown),
                "generated_date": date.today().isoformat(),
                **({"cheat_sheet_markdown": cheat_sheet} if cheat_sheet else {}),
            }},
            upsert=True,
        )
        new_or_changed.append(name)

    if not quota_exhausted:
        _ensure_dataweave_practice(chapters)

    return new_or_changed


def _ensure_dataweave_practice(chapters):
    db = get_db()
    match = next((c for c in chapters if c["name"] == DATAWEAVE_CHAPTER), None)
    if not match:
        return

    existing = db.dataweave_practice.find_one({"_id": "current"})
    if existing and existing.get("sha") == match["sha"]:
        return  # already generated for this version of the chapter

    logger.info("Generating DataWeave practice problems")
    text = fetch_chapter_text(match["download_url"])
    try:
        problems = generate_practice_problems(text)
    except GroqQuotaExhausted:
        logger.info("Groq daily quota reached - DataWeave practice problems will generate next run")
        return
    if not problems:
        return

    db.dataweave_practice.update_one(
        {"_id": "current"},
        {"$set": {"sha": match["sha"], "problems": problems}},
        upsert=True,
    )


def get_questions(chapter_name: str):
    doc = get_db().lecture_qna.find_one({"_id": chapter_name})
    return doc["questions_markdown"] if doc else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    updated = run()
    print(f"Generated/updated question sets for {len(updated)} chapter(s): {updated}")
