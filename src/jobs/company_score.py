"""Judges whether a company is worth applying to, using free/public signals:
recent Google News headlines about the company (layoffs, funding, controversies) plus
the LLM's own general knowledge. This intentionally does NOT scrape Glassdoor/AmbitionBox
(both 403 plain requests / are heavily bot-walled) - if you want ratings data in the mix,
the realistic option is entering it manually or pointing this at a paid ratings API later.
"""
import logging
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are helping a MuleSoft developer (3-5 yrs experience) decide whether a company is
worth applying to. Company: {company}

Recent news headlines about this company:
{headlines}

Based on the headlines and what you generally know about this company, give:
1. A score from 1-10 (10 = great place to apply, strong pay/stability/growth; 1 = avoid - active layoffs, bad reputation)
2. A one-paragraph verdict explaining the score, mentioning pay/stability signals if known

Output as:
Score: <n>
Verdict: <text>
"""


def fetch_recent_headlines(company: str, limit: int = 8):
    query = urllib.parse.quote(f'"{company}" (layoffs OR funding OR hiring OR salary)')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        titles = [item.findtext("title") for item in root.findall(".//item")]
        return titles[:limit]
    except Exception:
        logger.exception("News fetch failed for %s", company)
        return []


def score_company(company: str):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set (see .env.example)")

    headlines = fetch_recent_headlines(company)
    headline_text = "\n".join(f"- {h}" for h in headlines) or "(no recent news found)"

    client = Groq(api_key=GROQ_API_KEY.strip())
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(company=company, headlines=headline_text)}],
            temperature=0.3,
        )
    except Exception:
        logger.exception("Groq company-scoring call failed for %s", company)
        return None, ""

    text = response.choices[0].message.content.strip()
    score = None
    verdict = text
    for line in text.splitlines():
        if line.lower().startswith("score:"):
            try:
                score = int("".join(c for c in line.split(":", 1)[1] if c.isdigit()))
            except ValueError:
                pass
        if line.lower().startswith("verdict:"):
            verdict = line.split(":", 1)[1].strip()
    return score, verdict
