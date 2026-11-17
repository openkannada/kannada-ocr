# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Synthetic line images in Hugging Face parquet layout.

Each shard is `data/train-NNNNN-of-NNNNN.parquet` with an `image` column ({bytes, path}, PNG)
and a `text` column, which `datasets.load_dataset("parquet", ...)` and the Hub read
as an Image feature.
"""

from __future__ import annotations

import io
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

from .degrade import PROFILES, degrade, to_uint8
from .fonts import Font
from .render import render

GB = 1024**3
TO_LATIN = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")
TO_KANNADA = str.maketrans("0123456789", "೦೧೨೩೪೫೬೭೮೯")
PROFILE_WEIGHTS = (0.2, 0.4, 0.4)
SIZES = (24, 64)


@dataclass(frozen=True)
class Plan:
    lines: list[tuple[str, str]]
    fonts: list[Font]
    seed: int
    nudi: tuple[str | None, ...] = ()
    """Each line in Nudi glyph codes, or None if it cannot be encoded exactly. Needed
    only when `fonts` has legacy fonts."""
    profile_weights: tuple[float, float, float] = PROFILE_WEIGHTS
    """Shares of the clean, print and letterpress profiles."""

    def text_for(self, font: Font, index: int) -> str | None:
        """What to set in `font` for line `index`: the line, or its Nudi glyph codes."""
        if font.encoding == "nudi":
            return self.nudi[index] if index < len(self.nudi) else None
        return self.lines[index][1]


_plan: Plan | None = None


def _init(plan: Plan) -> None:
    global _plan
    _plan = plan


def label_for(font: Font, line: str) -> str:
    """The text a reader sees, for fonts that draw both digit sets alike."""
    if font.digit_style == "latin":
        return line.translate(TO_LATIN)
    if font.digit_style == "kannada":
        return line.translate(TO_KANNADA)
    return line


def make_sample(plan: Plan, index: int) -> dict[str, Any] | None:
    """1 rendered and degraded line, or None if no font tried can draw it exactly.

    A legacy font gets the line in Nudi glyph codes; the label stays the Unicode line,
    which kannadi guarantees the codes read back as."""
    rng = np.random.default_rng([plan.seed, index])
    designs = sorted({f.design for f in plan.fonts})
    line_index = int(rng.integers(len(plan.lines)))
    source, line = plan.lines[line_index]
    size = int(rng.integers(*SIZES))
    for _ in range(3):
        design = designs[int(rng.integers(len(designs)))]
        options = [f for f in plan.fonts if f.design == design]
        font = options[int(rng.integers(len(options)))]
        glyphs = plan.text_for(font, line_index)
        ink = render(font.face, glyphs, size) if glyphs is not None else None
        if ink is not None:
            break
    else:
        return None
    ghost_text = plan.text_for(font, int(rng.integers(len(plan.lines))))
    ghost = render(font.face, ghost_text, size) if ghost_text is not None else None
    profile = PROFILES[int(rng.choice(len(PROFILES), p=plan.profile_weights))]
    page, params = degrade(ink, profile, rng, ghost)
    buffer = io.BytesIO()
    Image.fromarray(to_uint8(page)).save(buffer, format="PNG")
    return {
        "image": {"bytes": buffer.getvalue(), "path": f"{index:08d}.png"},
        "text": label_for(font, line),
        "font": font.face.name,
        "design": font.design,
        "font_license": font.license,
        "font_encoding": font.encoding,
        "size": size,
        "text_source": source,
        "degradation": json.dumps(params, sort_keys=True),
    }


def _job(index: int) -> dict[str, Any] | None:
    assert _plan is not None
    return make_sample(_plan, index)


FEATURES = {
    "image": {"_type": "Image"},
    **{
        name: {"dtype": dtype, "_type": "Value"}
        for name, dtype in [
            ("text", "string"),
            ("font", "string"),
            ("design", "string"),
            ("font_license", "string"),
            ("font_encoding", "string"),
            ("size", "int64"),
            ("text_source", "string"),
            ("degradation", "string"),
        ]
    },
}
"""`datasets` reads these from the parquet schema; without them `image` is a plain struct."""


def with_features(table: pa.Table) -> pa.Table:
    metadata = {b"huggingface": json.dumps({"info": {"features": FEATURES}}).encode()}
    return table.replace_schema_metadata({**(table.schema.metadata or {}), **metadata})


def _write_shard(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(with_features(pa.Table.from_pylist(rows)), path, compression="zstd")


def generate(
    plan: Plan,
    out: Path,
    count: int,
    workers: int = 2,
    shard_size: int = 2000,
    max_bytes: int = 10 * GB,
    min_free: int = 15 * GB,
    log=print,
) -> dict[str, Any]:
    """Writes `count` samples, stopping early before the disk or size limits are crossed.

    `max_bytes` covers every run under `out.parent`, not only this one. Refuses to
    write into a run directory that already has shards, so 2 runs never mix.
    """
    if workers > 4:
        raise ValueError("at most 4 rendering processes are allowed")
    if any((out / "data").glob("*.parquet")):
        raise FileExistsError(f"{out / 'data'} already has shards; use a new --name")
    out.mkdir(parents=True, exist_ok=True)
    budget = Budget(max_bytes - tree_size(out.parent), min_free)
    rows: list[dict[str, Any]] = []
    shards: list[Path] = []
    written = skipped = 0
    stats: dict[str, Counter] = {
        "profile": Counter(),
        "design": Counter(),
        "text_source": Counter(),
    }
    stop = ""
    with Pool(workers, initializer=_init, initargs=(plan,)) as pool:
        for row in pool.imap(_job, range(count), chunksize=32):
            if row is None:
                skipped += 1
                continue
            rows.append(row)
            stats["profile"][json.loads(row["degradation"])["profile"]] += 1
            stats["design"][row["design"]] += 1
            stats["text_source"][row["text_source"]] += 1
            if len(rows) == shard_size:
                stop = _flush(rows, out, shards, budget)
                written += len(rows) if not stop.startswith("not written") else 0
                rows = []
                log(f"  {written}/{count}")
                if stop:
                    pool.terminate()
                    break
    if rows and not stop:
        stop = _flush(rows, out, shards, budget)
        written += len(rows) if not stop.startswith("not written") else 0
    final = []
    for i, shard in enumerate(shards):
        target = shard.with_name(f"train-{i:05d}-of-{len(shards):05d}.parquet")
        shard.rename(target)
        final.append(target.name)
    summary = {
        "samples": written,
        "skipped_missing_glyphs": skipped,
        "shards": final,
        "bytes": sum((out / "data" / f).stat().st_size for f in final),
        "stopped_early": stop or None,
        **{k: dict(sorted(v.items())) for k, v in stats.items()},
    }
    (out / "stats.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


@dataclass
class Budget:
    """Bytes this run may still write, and the free disk space to keep."""

    bytes_left: int
    min_free: int


def tree_size(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) if root.exists() else 0


def _flush(rows: list[dict[str, Any]], out: Path, shards: list[Path], budget: Budget) -> str:
    """Writes 1 shard unless a limit is already reached; returns a reason to stop, or ""."""
    if budget.bytes_left <= 0:
        return "not written: generated data reached its size limit"
    if shutil.disk_usage(out).free < budget.min_free:
        return "not written: free disk space is below the limit"
    path = out / "data" / f"shard-{len(shards):05d}.parquet"
    _write_shard(rows, path)
    shards.append(path)
    budget.bytes_left -= path.stat().st_size
    if budget.bytes_left <= 0:
        return "generated data reached its size limit"
    return ""


def preview(out: Path, path: Path, count: int = 24) -> None:
    """A contact sheet of the first `count` images, for a quick look."""
    shard = sorted((out / "data").glob("train-*.parquet"))[0]
    table = pq.read_table(shard, columns=["image"]).slice(0, count).to_pylist()
    images = [Image.open(io.BytesIO(r["image"]["bytes"])).convert("L") for r in table]
    width = max(im.width for im in images)
    sheet = Image.new("L", (width, sum(im.height + 4 for im in images)), 255)
    y = 0
    for im in images:
        sheet.paste(im, (0, y))
        y += im.height + 4
    sheet.save(path)
