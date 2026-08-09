from dataclasses import dataclass, field


@dataclass
class JobPosting:
    source: str            # "greenhouse", "lever", "linkedin", "naukri", "indeed"
    company: str
    title: str
    location: str
    url: str
    description: str
    external_id: str = ""  # source-side id, used for de-duping across daily runs
    posted_date: str = ""

    def dedupe_key(self) -> str:
        return f"{self.source}:{self.external_id or self.url}"
