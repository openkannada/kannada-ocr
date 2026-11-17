"""Readers for the MILE-IISc Kannada OCR datasets.

The page set is https://github.com/MILE-IISc/Kannada-OCR-test-images-with-ground-truth:
250 page scans at 300 dpi, with 1 XML file per page giving blocks, lines and words
with pixel boxes. The degraded word set is https://github.com/MILE-IISc/DegradedWordsKannada.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

NS = {"m": "http://mile.ee.iisc.ernet.in/schemas/ocr_output"}


@dataclass(frozen=True)
class Box:
    top: int
    bottom: int
    left: int
    right: int

    def padded(self, pad: int, width: int, height: int) -> tuple[int, int, int, int]:
        """The box grown by `pad` pixels and clipped to the image, as (left, top, right, bottom)."""
        return (
            max(0, self.left - pad),
            max(0, self.top - pad),
            min(width, self.right + 1 + pad),
            min(height, self.bottom + 1 + pad),
        )


@dataclass(frozen=True)
class Line:
    number: int
    text: str
    box: Box


@dataclass(frozen=True)
class Page:
    id: str
    book: str
    image: Path
    lines: tuple[Line, ...]

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


def parse_page(xml_path: Path, image_dir: Path) -> Page:
    """Reads 1 ground-truth XML file. Lines with no text are dropped."""
    root = ET.parse(xml_path).getroot()
    lines = []
    for block in root.iterfind(".//m:block", NS):
        for line in block.iterfind("m:line", NS):
            words = line.findall("m:word", NS)
            text = " ".join(w.get("unicode", "").strip() for w in words).strip()
            if text:
                lines.append(Line(int(line.get("LineNumber")), text, _line_box(block, line, words)))
    page_id = xml_path.stem
    return Page(
        id=page_id,
        book=page_id.rsplit("_P", 1)[0],
        image=image_dir / f"{page_id}.tif",
        lines=tuple(lines),
    )


def _int(element: ET.Element, name: str) -> int:
    return int(element.get(name) or 0)


def _line_box(block: ET.Element, line: ET.Element, words: list[ET.Element]) -> Box:
    """Line rows, with columns from the words when every word has a real box.

    About 30% of words in the page set carry no rows and zero columns; those lines
    take the block's columns instead.
    """
    if all(_int(w, "colEnd") > _int(w, "colStart") and w.get("rowStart") for w in words):
        left = min(_int(w, "colStart") for w in words)
        right = max(_int(w, "colEnd") for w in words)
        top = min(_int(line, "rowStart"), *(_int(w, "rowStart") for w in words))
        bottom = max(_int(line, "rowEnd"), *(_int(w, "rowEnd") for w in words))
    else:
        left, right = _int(block, "colStart"), _int(block, "colEnd")
        top, bottom = _int(line, "rowStart"), _int(line, "rowEnd")
    return Box(top=top, bottom=bottom, left=left, right=right)


def read_pages(repo: Path) -> list[Page]:
    """All pages of the MILE page set, sorted by id."""
    xml_files = sorted((repo / "groundtruth").glob("*.xml"))
    return [parse_page(p, repo / "images") for p in xml_files]


def read_degraded_words(repo: Path) -> list[tuple[Path, str]]:
    """(image, text) pairs from DegradedWordsKannada's GroundTruthUnicode.txt."""
    pairs = []
    lines = (repo / "GroundTruthUnicode.txt").read_text(encoding="utf-8-sig").splitlines()
    for line in lines[1:]:
        name, sep, text = line.partition(":")
        if not sep or not text.strip():
            continue
        pairs.append((repo / "TestImages" / name.strip(), text.strip()))
    return pairs
