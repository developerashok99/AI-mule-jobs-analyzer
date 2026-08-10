"""Splits the generated Q&A markdown (see generate_questions.py's fixed output format)
into individual structured questions, so the frontend can filter by level, track
per-question review state (spaced repetition), and quiz from the bank (mock interview)
without re-parsing markdown client-side."""
import hashlib
import re

_QUESTION_RE = re.compile(
    r"###\s*Q:\s*(?P<question>.+?)\s*\n"
    r"\*\*Level:\*\*\s*(?P<level>.+?)\s*\n"
    r"\*\*Answer:\*\*\s*(?P<answer>.+?)"
    r"(?=\n###\s*Q:|\Z)",
    re.DOTALL,
)


def parse_questions(chapter_name: str, markdown: str):
    """Returns [{"_id", "chapter", "question", "level", "answer"}, ...].
    _id is a stable hash of chapter+question text, so it stays the same across runs
    as long as the question text itself doesn't change (cache is keyed on chapter sha,
    so it only changes when the source chapter actually changes)."""
    questions = []
    for match in _QUESTION_RE.finditer(markdown):
        question = match.group("question").strip()
        level = match.group("level").strip()
        answer = match.group("answer").strip()
        qid = hashlib.sha1(f"{chapter_name}:{question}".encode()).hexdigest()[:16]
        questions.append({
            "_id": qid,
            "chapter": chapter_name,
            "question": question,
            "level": level,
            "answer": answer,
        })
    return questions
