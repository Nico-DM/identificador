from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchOutcome:
    urls: list[str]
    match_metadata: dict[str, dict]
    raw_payload: dict


class SearchEngine(ABC):
    """Strategy interface for reverse-image search providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique engine identifier (e.g. provider engine name)."""

    @abstractmethod
    def search(self, image_url: str, *, safe_search: bool = True) -> SearchOutcome:
        """Run reverse-image search and return normalized results."""
