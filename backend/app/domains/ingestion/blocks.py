"""RawBlock — the contract between extractors and the chunker.

Every extractor produces a list[RawBlock]. The chunker consumes only this type.
"""

from dataclasses import dataclass, field


BLOCK_TYPES = frozenset({"BODY", "HEADING", "CAPTION", "TABLE_ROW", "ALT_TEXT"})


@dataclass
class RawBlock:
    text: str
    source_id: str
    block_index: int
    page_or_position: str  # "page:3" | "ts:01:23:45" | "para:7"
    block_type: str = "BODY"  # BODY | HEADING | CAPTION | TABLE_ROW | ALT_TEXT
    language: str = "en"
    heading_path: list[str] = field(default_factory=list)  # ["Ch 1", "1.2 Methods"]

    def __post_init__(self) -> None:
        if self.block_type not in BLOCK_TYPES:
            raise ValueError(f"Unknown block_type: {self.block_type!r}")
