import io
import re

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTAnno, LTChar, LTFigure, LTTextBox, LTTextLine

from app.domains.ingestion.blocks import RawBlock
from app.domains.ingestion.extractors.base import BaseExtractor

_HEADING_RE = re.compile(r"^\d+(\.\d+)*\s+\S")  # "1.2 Introduction" style


class PDFExtractor(BaseExtractor):
    async def extract(self, content: bytes, source_id: str, url: str | None = None) -> list[RawBlock]:
        blocks: list[RawBlock] = []
        block_index = 0
        heading_path: list[str] = []

        params = LAParams(line_margin=0.5, char_margin=2.0)

        for page_num, page_layout in enumerate(
            extract_pages(io.BytesIO(content), laparams=params), start=1
        ):
            locator = f"page:{page_num}"
            for element in page_layout:
                if isinstance(element, LTFigure):
                    continue
                if not isinstance(element, LTTextBox):
                    continue

                text = element.get_text().strip()
                if not text:
                    continue

                # Determine block type heuristically
                avg_font_size = _avg_font_size(element)
                if avg_font_size and avg_font_size > 13:
                    block_type = "HEADING"
                    heading_path = _update_heading_path(heading_path, text)
                elif _HEADING_RE.match(text):
                    block_type = "HEADING"
                    heading_path = _update_heading_path(heading_path, text)
                else:
                    block_type = "BODY"

                blocks.append(
                    RawBlock(
                        text=text,
                        source_id=source_id,
                        block_index=block_index,
                        page_or_position=locator,
                        block_type=block_type,
                        heading_path=list(heading_path),
                    )
                )
                block_index += 1

        return blocks


def _avg_font_size(textbox: LTTextBox) -> float | None:
    sizes: list[float] = []
    for line in textbox:
        if not isinstance(line, LTTextLine):
            continue
        for char in line:
            if isinstance(char, LTChar):
                sizes.append(char.size)
    return sum(sizes) / len(sizes) if sizes else None


def _update_heading_path(current: list[str], heading_text: str) -> list[str]:
    # Shallow heuristic: reset to last heading on a new heading detection
    truncated = heading_text[:60].replace("\n", " ")
    if not current:
        return [truncated]
    return current[:-1] + [truncated] if len(current) > 1 else [truncated]
