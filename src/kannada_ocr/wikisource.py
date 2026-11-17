# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Proofread Kannada Wikisource pages paired with their scan images.

Only `/wiki/` paths are fetched: the Wikimedia robots.txt disallows `/w/` (which holds
api.php) for general crawlers, and allows `/wiki/` pages and `?action=raw`.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from .http import Client

SITE = "https://kn.wikisource.org"
INDEX_NS = "ಪರಿವಿಡಿ:"
PAGE_NS = "ಪುಟ:"
CATEGORIES = ("Category:Index_Validated", "Category:Index_Proofread")
KANNADA_DIGITS = "೦೧೨೩೪೫೬೭೮೯"
EXCLUDED_BOOKS = Path(__file__).resolve().parents[2] / "sources" / "excluded-training-books.json"


def excluded_books(path: Path = EXCLUDED_BOOKS) -> set[str]:
    """Scan file names never to train on, because their license tag on Commons is doubtful."""
    return {book["file"] for book in json.loads(path.read_text(encoding="utf-8"))}


def wiki_url(title: str, query: str = "") -> str:
    return f"{SITE}/wiki/{urllib.parse.quote(title.replace(' ', '_'))}{query}"


def kannada_number(n: int) -> str:
    return "".join(KANNADA_DIGITS[int(d)] for d in str(n))


def parse_number(text: str) -> int | None:
    digits = "".join(str(KANNADA_DIGITS.index(c)) if c in KANNADA_DIGITS else c for c in text)
    return int(digits) if digits.isdigit() else None


@dataclass(frozen=True)
class IndexInfo:
    title: str
    file: str
    fields: dict[str, str]
    pages: dict[int, int]
    """Page number to proofread quality level: 0 without text, 3 proofread, 4 validated."""

    @property
    def year(self) -> int | None:
        m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", self.fields.get("Year", ""))
        return int(m.group(1)) if m else None


@dataclass(frozen=True)
class ScanPage:
    title: str
    quality: int
    text: str
    image_url: str


def list_indexes(client: Client) -> list[str]:
    titles: set[str] = set()
    for category in CATEGORIES:
        body = client.get_text(wiki_url(category))
        for href in re.findall(r'href="/wiki/([^"#?]+)"', body):
            title = urllib.parse.unquote(href).replace("_", " ")
            if title.startswith(INDEX_NS):
                titles.add(title)
    return sorted(titles)


def _strip_tags(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def read_index(client: Client, title: str) -> IndexInfo:
    body = client.get_text(wiki_url(title))
    fields = {
        _strip_tags(label): _strip_tags(value)
        for label, value in re.findall(
            r'class="ws-index-label"[^>]*>(.*?)</t[dh]>\s*<t[dh][^>]*class="ws-index-value"[^>]*>(.*?)</t[dh]>',
            body,
            re.S,
        )
    }
    file = title.removeprefix(INDEX_NS)
    page_prefix = f"{PAGE_NS}{file}/".replace(" ", "_")
    pages: dict[int, int] = {}
    for href, quality in re.findall(
        r'<a href="/wiki/([^"?#]+)"[^>]*class="[^"]*prp-pagequality-(\d)', body
    ):
        href = urllib.parse.unquote(href)
        if href.startswith(page_prefix):
            number = parse_number(href[len(page_prefix) :])
            if number is not None:
                pages[number] = int(quality)
    return IndexInfo(title=title, file=file, fields=fields, pages=pages)


def file_licenses(client: Client, file: str) -> list[str]:
    """Short license names from the file's description page on Commons, or on Wikisource."""
    for url in (
        "https://commons.wikimedia.org/wiki/"
        + urllib.parse.quote("File:" + file.replace(" ", "_")),
        wiki_url("ಚಿತ್ರ:" + file),
    ):
        try:
            body = client.get_text(url)
        except Exception:  # noqa: BLE001 - a missing page just means "try the next host"
            continue
        names = re.findall(r'<span class="licensetpl_short"[^>]*>(.*?)</span>', body, re.S)
        if names:
            return sorted({_strip_tags(n) for n in names})
    return []


class _PageText(HTMLParser):
    """Visible text of a rendered Page, with block elements as line breaks."""

    BLOCK = {"p", "div", "br", "hr", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "center"}
    SKIP_CLASSES = ("reference", "mw-cite-backlink", "mw-editsection", "noprint")
    VOID = {"br", "hr", "img", "meta", "link", "input", "wbr", "col", "source"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[tuple[str, bool]] = []

    def _skipping(self) -> bool:
        return any(skip for _, skip in self.stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag in self.VOID:
            return
        classes = dict(attrs).get("class") or ""
        style = (dict(attrs).get("style") or "").replace(" ", "")
        skip = (
            tag in ("style", "script")
            or any(c in classes.split() for c in self.SKIP_CLASSES)
            or "display:none" in style
        )
        self.stack.append((tag, skip))

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        while self.stack:
            open_tag, _ = self.stack.pop()
            if open_tag == tag:
                break
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipping():
            self.parts.append(data.replace("\n", " "))


def page_text(page_html: str) -> str:
    """The proofread text of a rendered Page, 1 printed block per line, blank lines removed."""
    start = page_html.find('class="pagetext"')
    end = page_html.find('class="prp-page-image"')
    if start < 0:
        return ""
    fragment = page_html[page_html.rfind("<", 0, start) : end if end > start else None]
    parser = _PageText()
    parser.feed(fragment)
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if line)


def page_image_url(page_html: str) -> str | None:
    m = re.search(r'class="prp-page-image"><span><img src="([^"]+)"', page_html)
    if not m:
        return None
    url = html.unescape(m.group(1)).split("?", 1)[0]
    return "https:" + url if url.startswith("//") else url


def read_page(client: Client, index: IndexInfo, number: int) -> ScanPage | None:
    title = f"{PAGE_NS}{index.file}/{kannada_number(number)}"
    body = client.get_text(wiki_url(title))
    image = page_image_url(body)
    text = page_text(body)
    if not image or not text:
        return None
    return ScanPage(title=title, quality=index.pages.get(number, 0), text=text, image_url=image)


def sample_pages(index: IndexInfo, count: int, min_quality: int = 3) -> list[int]:
    """Up to `count` proofread page numbers spread evenly through the book.

    The first and last 5% are skipped, since covers and front matter are rarely body text.
    """
    numbers = sorted(n for n, q in index.pages.items() if q >= min_quality)
    if not numbers:
        return []
    margin = len(numbers) // 20
    body = numbers[margin : len(numbers) - margin] or numbers
    if len(body) <= count:
        return body
    step = len(body) / count
    return [body[int(i * step + step / 2)] for i in range(count)]
