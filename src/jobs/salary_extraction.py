"""Pulls a salary range out of free-text job descriptions.

None of Greenhouse/Lever/Workday expose a reliable structured salary field (checked -
`pay_input_ranges` on Greenhouse and `salaryRange` on Lever are both empty even on
postings that state a salary in the body). US pay-transparency laws mean many US
postings state it inline in plain text instead, e.g. "$128,560 - $160,700" - this
module extracts that with regex. Best-effort: most non-US postings (especially Indian
ones) don't state salary at all, so a lot of jobs will legitimately have no match.
"""
import re

# Ordered by specificity - LPA/lakh patterns must be tried before generic number patterns
_PATTERNS = [
    # INR lakhs: "₹8-12 LPA", "8 to 12 LPA", "INR 8-12 Lakhs"
    (
        "INR",
        re.compile(
            r"(?:₹|INR|Rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:LPA|Lakhs?(?:\s*per\s*annum)?)",
            re.IGNORECASE,
        ),
        100_000,  # 1 lakh
    ),
    # USD/GBP/EUR with thousands separators: "$128,560 - $160,700", "£50,000-£70,000"
    (
        None,  # currency symbol captured directly
        re.compile(r"([$£€])\s*([\d,]{4,})\s*(?:-|to|–)\s*[$£€]?\s*([\d,]{4,})"),
        1,
    ),
    # USD/GBP/EUR shorthand: "$120k - $150k", "£50k-£70k"
    (
        None,
        re.compile(r"([$£€])\s*(\d+)\s*[kK]\s*(?:-|to|–)\s*[$£€]?\s*(\d+)\s*[kK]"),
        1_000,
    ),
]

_CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR"}


def extract_salary(text: str):
    """Returns {"salary_min": int, "salary_max": int, "currency": str, "salary_text": str}
    or None if no salary range was found."""
    if not text:
        return None

    for currency, pattern, multiplier in _PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        groups = match.groups()
        if currency is None:
            # symbol-based patterns capture the currency as the first group
            symbol, low, high = groups
            currency = _CURRENCY_SYMBOLS.get(symbol, "USD")
        else:
            low, high = groups

        try:
            low_val = int(float(str(low).replace(",", "")) * multiplier)
            high_val = int(float(str(high).replace(",", "")) * multiplier)
        except ValueError:
            continue

        if low_val <= 0 or high_val <= 0 or low_val > high_val:
            continue

        return {
            "salary_min": low_val,
            "salary_max": high_val,
            "currency": currency,
            "salary_text": match.group(0).strip(),
        }

    return None


def apply_salary(job):
    """Mutates a JobPosting in place, filling salary_* fields from its description
    if the source didn't already provide structured salary data. Returns the job
    for convenient chaining."""
    if job.salary_min:
        return job  # source already gave us structured salary (e.g. RemoteOK)

    found = extract_salary(f"{job.title} {job.description}")
    if found:
        job.salary_min = found["salary_min"]
        job.salary_max = found["salary_max"]
        job.salary_currency = found["currency"]
        job.salary_text = found["salary_text"]
    return job
