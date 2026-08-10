from dataclasses import dataclass


@dataclass
class JobPosting:
    source: str            # "greenhouse", "lever", "workday", "remoteok", "arbeitnow", "linkedin", "naukri", "indeed"
    company: str
    title: str
    location: str
    url: str
    description: str
    external_id: str = ""  # source-side id, used for de-duping across daily runs
    posted_date: str = ""
    salary_min: int = 0
    salary_max: int = 0
    salary_currency: str = ""
    salary_text: str = ""  # raw matched string, e.g. "$128,560 - $160,700"

    def dedupe_key(self) -> str:
        return f"{self.source}:{self.external_id or self.url}"
