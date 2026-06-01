import re

import html2text
import httpx

from app.domains.ingestion.blocks import RawBlock
from app.domains.ingestion.extractors.base import BaseExtractor

_STRIP_WS_RE = re.compile(r"\n{3,}")


class WebExtractor(BaseExtractor):
    """Extract RawBlocks from a web page via httpx (static HTML only).

    JS-rendered pages (SPAs) require Playwright — deferred to M2.
    Robots.txt compliance: we respect it at the service layer before calling
    this extractor; the extractor itself just fetches and parses.
    """

    async def extract(self, content: bytes, source_id: str, url: str | None = None) -> list[RawBlock]:
        html = content.decode("utf-8", errors="replace")
        return _parse_html(html, source_id, url)

    @classmethod
    async def fetch_and_extract(cls, url: str, source_id: str) -> list[RawBlock]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
            headers={"User-Agent": "KnowledgeCommons/0.1 (+https://github.com/knowledge-commons)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
        return _parse_html(response.text, source_id, url)


def _parse_html(html: str, source_id: str, url: str | None) -> list[RawBlock]:
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    converter.ignore_emphasis = False
    converter.body_width = 0  # no line wrapping

    markdown = converter.handle(html)
    # Collapse excessive blank lines
    markdown = _STRIP_WS_RE.sub("\n\n", markdown).strip()

    blocks: list[RawBlock] = []
    block_index = 0
    heading_path: list[str] = []
    para_num = 0

    for para in markdown.split("\n\n"):
        para = para.strip()
        if not para:
            continue

        para_num += 1
        locator = f"para:{para_num}"

        if para.startswith("#"):
            # Markdown heading
            text = para.lstrip("#").strip()
            heading_path = [text[:60]]
            block_type = "HEADING"
        else:
            text = para
            block_type = "BODY"

        if len(text) < 20:  # skip very short fragments (nav links, etc.)
            continue

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
