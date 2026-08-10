"""Generates DataWeave transformation practice problems from the DataWeave chapter -
reveal-based self-check (shows expected output for you to compare against your own
attempt) rather than automated grading, since there's no real Mule/DataWeave runtime
available here to actually execute and verify an expression."""
import json
import logging

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are creating DataWeave practice problems for a MuleSoft developer with 3-5 years of
experience, based on the chapter notes below. Produce 8 practice problems of increasing difficulty, grounded in
the functions/patterns actually mentioned in the notes.

Each problem needs:
- a short task description (what transformation to write)
- a small sample input payload (valid JSON, realistic size - 3-8 fields)
- the exact expected output (valid JSON) after applying the correct DataWeave transformation
- the reference DataWeave expression/script that produces it
- difficulty: "easy", "medium", or "hard"

Respond with ONLY a JSON array, no markdown fences, no commentary, in this exact shape:
[
  {{
    "task": "...",
    "sample_input": {{...}},
    "expected_output": {{...}},
    "reference_solution": "...",
    "difficulty": "easy"
  }}
]

Chapter notes:
---
{chapter_text}
---
"""


def generate_practice_problems(chapter_text: str):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set (see .env.example)")

    client = Groq(api_key=GROQ_API_KEY.strip())
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(chapter_text=chapter_text[:12000])}],
            temperature=0.5,
        )
        text = response.choices[0].message.content.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        problems = json.loads(text)
    except Exception:
        logger.exception("DataWeave practice problem generation failed")
        return []

    for i, problem in enumerate(problems):
        problem["_id"] = f"dw-{i}"
    return problems
