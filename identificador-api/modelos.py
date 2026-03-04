from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class DateCandidate:
    date: datetime
    source: str
    raw: str
    extractor: str
    url: str
    score: float = 0.0
    flags: Dict[str, bool] = field(default_factory=dict)

