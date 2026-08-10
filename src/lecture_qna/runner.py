"""Walks every lecture chapter and generates interview Q&A for new/changed chapters only.
Results and the per-chapter cache (by GitHub blob sha) both live in MongoDB, so nothing
needs to be committed back to the repo from CI."""
import logging

from src.jobs.store import get_db
from src.lecture_qna.fetch_notes import list_chapters, fetch_chapter_text
from src.lecture_qna.generate_questions import generate_questions_for_chapter

logger = logging.getLogger(__name__)


def run():
    collection = get_db().lecture_qna
    chapters = list_chapters()

    new_or_changed = []
    for chapter in chapters:
        name, sha = chapter["name"], chapter["sha"]
        cached = collection.find_one({"_id": name})
        if cached and cached.get("sha") == sha:
            continue  # already generated for this exact version of the chapter

        logger.info("Generating interview questions for: %s", name)
        text = fetch_chapter_text(chapter["download_url"])
        qa_markdown = generate_questions_for_chapter(name, text)
        if not qa_markdown:
            continue  # LLM call failed, leave cache untouched so it's retried next run

        collection.update_one(
            {"_id": name},
            {"$set": {"sha": sha, "questions_markdown": qa_markdown}},
            upsert=True,
        )
        new_or_changed.append(name)

    return new_or_changed


def get_questions(chapter_name: str):
    doc = get_db().lecture_qna.find_one({"_id": chapter_name})
    return doc["questions_markdown"] if doc else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    updated = run()
    print(f"Generated/updated question sets for {len(updated)} chapter(s): {updated}")
