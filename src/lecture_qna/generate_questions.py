"""Generates likely interview questions (+ model answers) from a lecture chapter,
pitched at a 3-5 year MuleSoft developer level."""
import logging
import os

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL
from src.groq_errors import raise_if_quota_exhausted

logger = logging.getLogger(__name__)

MAX_CHAPTER_CHARS = 12000  # keeps prompt + response comfortably under Groq free-tier TPM limits

PROMPT_TEMPLATE = """You are helping a MuleSoft developer with 3-5 years of experience prepare for job interviews.
Below is one chapter of their study notes. Based ONLY on what's actually covered in this chapter, produce likely
interview questions a company would ask a mid-to-senior (3-5 yrs) MuleSoft Developer candidate about this topic.

Cover a mix of:
- Conceptual questions ("explain X", "what's the difference between X and Y")
- Scenario/design questions ("how would you handle...", "how would you design a flow that...")
- "Gotcha"/debugging questions based on any pitfalls or common errors mentioned in the notes

For each question give a concise model answer (3-6 sentences) a candidate could actually say out loud, grounded in
the notes below. Skip trivial/fresher-level questions that a 3-5 yr candidate would never realistically be asked.

Output as markdown with this exact structure per question:

### Q: <question>
**Level:** <Conceptual | Scenario/Design | Debugging>
**Answer:** <model answer>

Chapter notes:
---
{chapter_text}
---
"""


def generate_questions_for_chapter(chapter_title: str, chapter_text: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set (see .env.example)")

    client = Groq(api_key=GROQ_API_KEY.strip())
    trimmed = chapter_text[:MAX_CHAPTER_CHARS]

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": PROMPT_TEMPLATE.format(chapter_text=trimmed)},
            ],
            temperature=0.4,
        )
    except Exception as exc:
        raise_if_quota_exhausted(exc)
        logger.exception("Groq question-generation call failed for chapter: %s", chapter_title)
        return ""

    return response.choices[0].message.content.strip()
