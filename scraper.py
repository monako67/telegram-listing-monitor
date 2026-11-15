from __future__ import annotations

import asyncio
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = next((value for key, value in attrs if key.lower() == "href"), None)
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            title = " ".join(" ".join(self._text).split())
            self.links.append((self._href, title))
            self._href = None
            self._text = []


def extract_items(search_url: str, html: str, limit: int = 100) -> list[tuple[str, str]]:
    parser = LinkParser()
    parser.feed(html)
    source = urlsplit(search_url)
    search_url = urldefrag(search_url).url
    seen: set[str] = set()
    result: list[tuple[str, str]] = []

    for href, title in parser.links:
        url = urldefrag(urljoin(search_url, href)).url
        target = urlsplit(url)
        if not title or target.scheme not in {"http", "https"}:
            continue
        if target.netloc.lower() != source.netloc.lower() or url == search_url or url in seen:
            continue
        seen.add(url)
        result.append((url, title[:300]))
        if len(result) >= limit:
            break
    return result


def _download(url: str, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=25) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"Unsupported content type: {content_type}")
        body = response.read(5_000_001)
        if len(body) > 5_000_000:
            raise ValueError("Page exceeds the 5 MB limit")
        return body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


async def fetch_items(url: str, limit: int, user_agent: str) -> list[tuple[str, str]]:
    html = await asyncio.to_thread(_download, url, user_agent)
    return extract_items(url, html, limit)


