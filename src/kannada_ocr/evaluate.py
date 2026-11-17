"""Runs a recognizer over a benchmark set and scores it with kannadi-aware metrics."""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from . import text
from .dataset import read_jsonl


class Recognizer(Protocol):
    name: str
    workers: int
    config: str
    """Everything that changes the output: a saved prediction with another config is redone."""

    def recognize(self, image: Path, level: str) -> str: ...


def select(rows: list[dict[str, Any]], split: str | None, limit: int | None) -> list[dict]:
    """Rows of 1 split, and with `limit` a fixed pseudo-random sample of them."""
    chosen = [r for r in rows if split is None or r["split"] == split]
    if limit is not None and limit < len(chosen):
        chosen = sorted(chosen, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())
        chosen = sorted(chosen[:limit], key=lambda r: r["id"])
    return chosen


def evaluate(
    recognizer: Recognizer,
    bench: Path,
    results: Path,
    split: str | None = "test",
    limit: int | None = None,
    log=print,
    transform: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Recognizes every selected image, then writes and returns a summary.

    Predictions are appended to `<results>/<model>/<set>.predictions.jsonl` as they
    arrive, so an interrupted run resumes where it stopped. A saved prediction is reused
    only if its image hash and recognizer config still match. A `transform` is applied
    to predictions before scoring, for diagnostics; its name goes in the summary file name.
    """
    available = select(read_jsonl(bench / "metadata.jsonl"), split, None)
    rows = select(available, None, limit)
    if not rows:
        raise ValueError(f"{bench.name} has no {split or 'any'} items to score")
    out = results / recognizer.name
    out.mkdir(parents=True, exist_ok=True)
    predictions_path = out / f"{bench.name}.predictions.jsonl"
    saved = read_jsonl(predictions_path, allow_torn_tail=True) if predictions_path.exists() else []
    images = {r["id"]: image_hash(bench / r["file_name"]) for r in rows}
    done = {
        p["id"]: p
        for p in saved
        if p.get("config") == recognizer.config and p.get("image") == images.get(p["id"])
    }
    todo = [r for r in rows if r["id"] not in done]
    log(f"{recognizer.name} on {bench.name}: {len(rows)} items, {len(todo)} to run")

    def run(row: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        hyp = recognizer.recognize(bench / row["file_name"], row["level"])
        return {
            "id": row["id"],
            "hyp": hyp,
            "seconds": round(time.perf_counter() - start, 3),
            "image": images[row["id"]],
            "config": recognizer.config,
        }

    with (
        predictions_path.open("a", encoding="utf-8") as f,
        ThreadPoolExecutor(recognizer.workers) as pool,
    ):
        for n, prediction in enumerate(pool.map(run, todo), 1):
            done[prediction["id"]] = prediction
            f.write(json.dumps(prediction, ensure_ascii=False) + "\n")
            f.flush()
            if n % 200 == 0:
                log(f"  {n}/{len(todo)}")

    fix = transform or (lambda hyp: hyp)
    hyps = [fix(done[r["id"]]["hyp"]) for r in rows]
    report = text.score([(r["id"], r["text"], h) for r, h in zip(rows, hyps, strict=True)])
    summary = {
        "model": recognizer.name,
        "set": bench.name,
        "split": split or "all",
        "transform": transform.__name__ if transform else None,
        "sampled_from": len(available),
        "date": datetime.now(UTC).date().isoformat(),
        "seconds_per_item": round(
            sum(done[r["id"]]["seconds"] for r in rows) / max(1, len(rows)), 3
        ),
        **report["summary"],
        "wrong_script_items": sum(text.other_indic_script(h) for h in hyps),
        "cer_by_group": _cer_by_group(rows, report["items"]),
    }
    suffix = f".n{len(rows)}" if len(rows) < len(available) else ""
    if transform:
        suffix += f".{transform.__name__}"
    (out / f"{bench.name}.{split or 'all'}{suffix}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n"
    )
    log(
        f"  CER {summary['cer']:.4f}  WER {summary['wer']:.4f}  AER {summary['aer']:.4f}"
        f"  ({summary['items']} items)"
    )
    return summary


def image_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _cer_by_group(rows: list[dict[str, Any]], items: list[dict[str, Any]]) -> dict[str, float]:
    edits: dict[str, int] = defaultdict(int)
    length: dict[str, int] = defaultdict(int)
    for row, item in zip(rows, items, strict=True):
        edits[row["group"]] += item["char_edits"]
        length[row["group"]] += item["ref_chars"]
    return {g: round(edits[g] / length[g], 4) if length[g] else 0.0 for g in sorted(edits)}
