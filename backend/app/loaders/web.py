"""Web page loader using readability + requests."""

import hashlib
import re
from html.parser import HTMLParser

import httpx


class SimpleTextExtractor(HTMLParser):
    """Lightweight HTML text extractor (no lxml dependency)."""

    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript"}

    def __init__(self):
        super().__init__()
        self._text_parts: list[str] = []
        self._skip_depth = 0
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._skip_depth += 1  # handled in data

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag in ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            self._text_parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            # Check for title
            if hasattr(self, '_in_title'):
                self.title = data.strip()
            return
        text = data.strip()
        if text:
            self._text_parts.append(text)

    def get_text(self) -> str:
        raw = " ".join(self._text_parts)
        # Clean up whitespace
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r"[ \t]+", " ", raw)
        return raw.strip()


async def fetch_webpage(url: str) -> tuple[str, str]:
    """Fetch and extract text from a URL. Returns (title, text)."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ObsidianRAG/1.0)"},
        )
        response.raise_for_status()

    parser = SimpleTextExtractor()
    parser.feed(response.text)
    title = parser.title or url.split("/")[-1] or "Web Page"
    text = parser.get_text()

    return title, text


def chunk_web_text(text: str, title: str, url: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """Chunk web page text into documents."""
    documents = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()

        if len(chunk_text) < 50:
            start += chunk_size - overlap
            continue

        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
        doc_id = f"web:{url}:{content_hash}"

        documents.append({
            "id": doc_id,
            "text": chunk_text,
            "metadata": {
                "source_type": "web",
                "file_name": title,
                "url": url,
                "heading_path": title,
                "content_hash": content_hash,
            },
        })

        start += chunk_size - overlap

    return documents


async def load_webpage(url: str) -> list[dict]:
    """Load a webpage and return document chunks."""
    title, text = await fetch_webpage(url)
    return chunk_web_text(text, title, url)
