from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DateCandidate:
    date: datetime
    source: str
    raw: str
    extractor: str
    url: str
    score: float = 0.0
    flags: dict[str, bool] = field(default_factory=dict)
