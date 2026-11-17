"""Ground truth for tesstrain, and the `.lstmf` files lstmtraining reads.

`export` writes 1 PNG and 1 `.gt.txt` file per line image, which tesstrain uses for the
unicharset and the proto model. Labels go through kannadi normalization, as references do when
scored. Each source is sampled by a hash of its item ids, so the same arguments always pick the
same lines. `pack` turns the lines into `.lstmf` files a few hundred lines at a time, because
tesstrain's 1 Tesseract call per line manages about 6 lines per second.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import unicodedata
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

from . import text
from .dataset import read_jsonl
from .http import Client

LANGDATA_COMMIT = "07930fd9f246622c26eb5de794d9212ceac432d3"
LANGDATA_URL = f"https://raw.githubusercontent.com/tesseract-ocr/langdata_lstm/{LANGDATA_COMMIT}/"
LANGDATA_FILES = ("radical-stroke.txt", "Kannada.unicharset", "Latin.unicharset")
"""What combine_lang_model reads for Kannada with Latin digits and punctuation (Apache 2.0)."""

Item = tuple[str, bytes | Path, str]
"""Item id, PNG bytes or a grayscale PNG file, and label."""


@dataclass(frozen=True)
class Source:
    name: str
    root: Path
    split: str | None = None
    """For an ImageFolder set: the split to take. Synthetic parquet sets have none."""
    count: int | None = None
    """How many items to sample; all of them if None."""
    font_license: str | None = None
    """For a synthetic set: only lines rendered in fonts under this license."""


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("L").save(buffer, format="PNG")
    return buffer.getvalue()


def _rank(item_id: str) -> str:
    return hashlib.sha256(item_id.encode()).hexdigest()


def _imagefolder(source: Source) -> Iterator[Item]:
    rows = [
        row
        for row in read_jsonl(source.root / "metadata.jsonl")
        if source.split is None or row.get("split") == source.split
    ]
    rows.sort(key=lambda row: _rank(row["id"]))
    for row in rows[: source.count]:
        path = source.root / row["file_name"]
        with Image.open(path) as image:
            ready = image.format == "PNG" and image.mode == "L"
            yield row["id"], path if ready else _png(image), row["text"]


def _parquet(source: Source) -> Iterator[Item]:
    ids = []
    for shard in sorted((source.root / "data").glob("*.parquet")):
        licenses = pq.read_table(shard, columns=["font_license"]).column(0).to_pylist()
        ids += [
            (f"{shard.stem}_{i:05d}", shard, i)
            for i, license in enumerate(licenses)
            if source.font_license is None or license == source.font_license
        ]
    ids.sort(key=lambda entry: _rank(entry[0]))
    wanted: dict[Path, dict[int, str]] = {}
    for item_id, shard, i in ids[: source.count]:
        wanted.setdefault(shard, {})[i] = item_id
    found: dict[str, Item] = {}
    for shard, rows in wanted.items():
        table = pq.read_table(shard, columns=["image", "text"]).take(sorted(rows))
        for i, image, label in zip(
            sorted(rows),
            table.column("image").to_pylist(),
            table.column("text").to_pylist(),
            strict=True,
        ):
            found[rows[i]] = (rows[i], image["bytes"], label)
    return (found[item_id] for item_id, _, _ in ids[: source.count])


def items(source: Source) -> list[Item]:
    """The source's items, sampled to `count` by a hash of their ids, in that order."""
    is_parquet = (source.root / "data").is_dir()
    return list(_parquet(source) if is_parquet else _imagefolder(source))


EXPLICIT_VIRAMA = re.compile("\u0ccd(?![\u0c95-\u0cb9\u0cde\u200c\u200d])")
"""A virama not followed by a consonant (U+0C95 to U+0CB9, U+0CDE) or a joiner."""


JOINED_VIRAMA = re.compile("\u0ccd\u200c(?=[\u0c95-\u0cb9\u0cde])")


def tesseract_label(label: str) -> str:
    """The label in the units Tesseract's Kannada unicharset can encode.

    A virama that ends a word becomes U+0CCD U+200C, and a ZWNJ between a virama and a
    consonant is dropped, since lstmtraining cannot encode either otherwise. Scoring ignores
    ZWNJ, so neither change alters what is scored.
    """
    return EXPLICIT_VIRAMA.sub("\u0ccd\u200c", JOINED_VIRAMA.sub("\u0ccd", label))


PACK_SIZE = 400


def wordstr_box(label: str, width: int, height: int, page: int = 0) -> str:
    """The WordStr box lines tesstrain's generate_wordstr_box.py writes for a left-to-right
    label, for page `page` of a multi-page image."""
    if any(unicodedata.bidirectional(c) in ("R", "AL", "RLE", "RLO", "RLI") for c in label):
        raise ValueError(f"right-to-left text is not supported: {label!r}")
    line = unicodedata.normalize("NFC", label.strip())
    return f"WordStr 0 0 {width} {height} {page} #{line}\n\t 0 0 {width} {height} {page}\n"


def export(sources: list[Source], gt_dir: Path) -> dict[str, int]:
    """Writes each source's lines into `gt_dir` and returns how many each gave.

    Refuses a non-empty `gt_dir`, so 2 exports never mix.
    """
    if gt_dir.exists() and any(gt_dir.iterdir()):
        raise FileExistsError(f"{gt_dir} is not empty")
    gt_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for source in sources:
        chosen = items(source)
        labels = text.normalize([" ".join(label.split()) for _, _, label in chosen])
        written = 0
        for (item_id, png, _), label in zip(chosen, labels, strict=True):
            if not label.strip() or text.other_indic_script(label):
                continue  # some proofread pages keep Telugu letters left by old OCR
            label = tesseract_label(label)
            stem = f"{source.name}_{item_id}"
            if isinstance(png, Path):
                os.link(png, gt_dir / f"{stem}.png")  # a hard link costs no disk
            else:
                (gt_dir / f"{stem}.png").write_bytes(png)
            (gt_dir / f"{stem}.gt.txt").write_text(label + "\n", encoding="utf-8")
            written += 1
        counts[source.name] = written
    manifest = {
        "sources": [
            {
                "name": s.name,
                "root": str(s.root),
                "split": s.split,
                "count": s.count,
                "font_license": s.font_license,
            }
            for s in sources
        ],
        "lines": counts,
    }
    (gt_dir.parent / f"{gt_dir.name}.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return counts


def _pack_one(gt_dir: Path, stems: list[str], base: Path) -> Path:
    lstmf = base.with_suffix(".lstmf")
    if lstmf.exists():
        return lstmf
    part = base.with_name(base.name + "-part")
    images = [Image.open(gt_dir / f"{stem}.png").convert("L") for stem in stems]
    boxes = [
        wordstr_box((gt_dir / f"{stem}.gt.txt").read_text(encoding="utf-8"), *image.size, page)
        for page, (stem, image) in enumerate(zip(stems, images, strict=True))
    ]
    tif, box = part.with_name(part.name + ".tif"), part.with_name(part.name + ".box")
    images[0].save(tif, save_all=True, append_images=images[1:], compression="tiff_lzw")
    box.write_text("".join(boxes), encoding="utf-8")
    subprocess.run(
        ["tesseract", str(tif), str(part), "--psm", "13", "lstm.train"],
        capture_output=True,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        check=True,
    )
    tif.unlink()
    box.unlink()
    part.with_name(part.name + ".lstmf").rename(lstmf)
    for stem in stems:
        (gt_dir / f"{stem}.png").unlink()
    return lstmf


def pack(gt_dir: Path, out_dir: Path, size: int = PACK_SIZE, workers: int = 2) -> list[Path]:
    """Writes every line in `gt_dir` into `.lstmf` files of `size` lines and returns them.

    Lines are ordered by a hash of their names, so each file mixes the sources. A line's PNG is
    deleted once its pack is written, and its `.gt.txt` stays. A rerun keeps the files already
    written.
    """
    stems = sorted((p.name.removesuffix(".gt.txt") for p in gt_dir.glob("*.gt.txt")), key=_rank)
    if not stems:
        raise FileNotFoundError(f"{gt_dir} has no .gt.txt files")
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks = [stems[i : i + size] for i in range(0, len(stems), size)]
    with ThreadPoolExecutor(workers) as pool:
        return list(
            pool.map(
                lambda k: _pack_one(gt_dir, chunks[k], out_dir / f"pack-{k:04d}"),
                range(len(chunks)),
            )
        )


def fetch_langdata(client: Client, dest: Path) -> list[Path]:
    """The langdata files tesstrain needs, from a fixed commit of tesseract-ocr/langdata_lstm."""
    return [client.download(LANGDATA_URL + name, dest / name) for name in LANGDATA_FILES]
