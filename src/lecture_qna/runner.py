"""Walks every lecture chapter, generates interview Q&A for new/changed chapters only,
and writes results to data/lecture_qna/<chapter>.md."""
import json
import logging
import os

from src.config import DATA_DIR
from src.lecture_qna.fetch_notes import list_chapters, fetch_chapter_text
from src.lecture_qna.generate_questions import generate_questions_for_chapter

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(DATA_DIR, "lecture_qna")
CACHE_PATH = os.path.join(DATA_DIR, "lecture_qna_cache.json")


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cache = _load_cache()
    chapters = list_chapters()

    new_or_changed = []
    for chapter in chapters:
        name, sha = chapter["name"], chapter["sha"]
        if cache.get(name) == sha:
            continue  # already generated for this exact version of the chapter

        logger.info("Generating interview questions for: %s", name)
        text = fetch_chapter_text(chapter["download_url"])
        qa_markdown = generate_questions_for_chapter(name, text)
        if not qa_markdown:
            continue  # LLM call failed, leave cache untouched so it's retried next run

        out_path = os.path.join(OUTPUT_DIR, name.replace(" ", "_"))
        with open(out_path, "w") as f:
            f.write(f"# Interview Questions: {name}\n\n{qa_markdown}\n")

        cache[name] = sha
        new_or_changed.append(name)

    _save_cache(cache)
    return new_or_changed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    updated = run()
    print(f"Generated/updated question sets for {len(updated)} chapter(s): {updated}")
