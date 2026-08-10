"""Generates a condensed one-page revision sheet per chapter - for a night-before skim,
not a substitute for the full Q&A set."""
import logging

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Condense this MuleSoft chapter into a one-page revision cheat sheet for a 3-5 year developer
about to walk into an interview. Be terse - this is for a last-minute skim, not learning from scratch.

Output as markdown with exactly these sections:

## Key terms
(5-10 terms, each with a one-line definition)

## Must-know facts
(bullet list of the specific facts/behaviors/gotchas someone would need to state precisely, not vaguely)

## Most-asked questions
(the 3 questions from this chapter most likely to come up, no answers - just the questions, as a reminder of
what to be ready for)

## Common mistakes
(pitfalls explicitly mentioned in the notes, if any)

Chapter notes:
---
{chapter_text}
---
"""


def generate_cheat_sheet(chapter_title: str, chapter_text: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set (see .env.example)")

    client = Groq(api_key=GROQ_API_KEY.strip())
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(chapter_text=chapter_text[:12000])}],
            temperature=0.3,
        )
    except Exception:
        logger.exception("Cheat sheet generation failed for chapter: %s", chapter_title)
        return ""

    return response.choices[0].message.content.strip()
