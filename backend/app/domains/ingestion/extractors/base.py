from abc import ABC, abstractmethod

from app.domains.ingestion.blocks import RawBlock


class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, content: bytes, source_id: str, url: str | None = None) -> list[RawBlock]:
        """Extract RawBlocks from raw content bytes."""
        ...
