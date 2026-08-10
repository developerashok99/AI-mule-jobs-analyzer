"""Shared handling for Groq's free-tier daily token cap (100k tokens/day at time of
writing). When it's hit, every subsequent call in the same run will also fail - so
generation code should stop trying rather than burn through 20 more failed calls, and
let whatever's left roll over to the next scheduled run instead."""
import groq


class GroqQuotaExhausted(Exception):
    """Raised when Groq returns a 429 for hitting the daily token cap specifically
    (not a per-minute rate limit, which is transient and worth retrying)."""


def raise_if_quota_exhausted(exc: Exception):
    if isinstance(exc, groq.RateLimitError) and "tokens per day" in str(exc).lower():
        raise GroqQuotaExhausted(str(exc)) from exc
