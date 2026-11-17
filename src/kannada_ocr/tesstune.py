# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Fine-tunes a Tesseract model in rounds and keeps the round that scores best on dev.

lstmtraining keeps the checkpoint with the lowest training error, which says little about new
books. Each round here trains a fixed number of lines, converts the checkpoint to a model,
and scores it on dev lines and dev pages with the benchmark's own scorer. Training stops
when the dev score has not improved for `patience` rounds, and the best round becomes the model.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .baselines.tesseract import Tesseract
from .evaluate import evaluate

MIN_DELTA = 0.001
"""0.1 points of CER: smaller changes are within noise on the dev set."""
DEV_SETS = (("mile-lines", 600, 3), ("wikisource-old", None, 4))
"""Dev set, sample size and page mode. Lines ignore the mode; old print reads better in mode 4."""


@dataclass(frozen=True)
class Settings:
    learning_rate: float | None = 0.0001
    """lstmtraining's default for fine-tuning; None keeps the rate stored in the start model."""
    round_lines: int = 10_000
    max_rounds: int = 12
    patience: int = 2


@dataclass(frozen=True)
class Round:
    lines: int
    dev_cer: float
    scores: dict[str, float]


def should_stop(scores: list[float], patience: int, min_delta: float = MIN_DELTA) -> bool:
    """True when none of the last `patience` scores beat the best earlier one by `min_delta`."""
    if len(scores) <= patience:
        return False
    best_before = min(scores[:-patience])
    return all(score > best_before - min_delta for score in scores[-patience:])


def best_round(rounds: list[Round]) -> int:
    """Index of the round with the lowest dev CER; the earliest one on a tie."""
    return min(range(len(rounds)), key=lambda i: (rounds[i].dev_cer, i))


def dev_score(tessdata: Path, lang: str, bench: Path, results: Path) -> dict[str, float]:
    scores = {}
    for name, limit, mode in DEV_SETS:
        recognizer = Tesseract(tessdata, lang=lang, page_mode=mode)
        summary = evaluate(recognizer, bench / name, results, "dev", limit, log=lambda _: None)
        scores[name] = summary["cer"]
    return scores


def tune_dir(out: Path, settings: Settings) -> Path:
    rate = settings.learning_rate
    return out / ("tune-stored" if rate is None else f"tune-lr{rate:g}")


def _lstmtraining(*args: str, log: Path) -> None:
    start = log.stat().st_size if log.exists() else 0
    with log.open("a") as output:
        status = subprocess.run(["lstmtraining", *args], stdout=output, stderr=output).returncode
    # Its eval thread can fail an assert (num_docs > 0) at exit, after the checkpoint is written.
    if status and b"\nFinished! " not in log.read_bytes()[start:]:
        raise RuntimeError(f"lstmtraining failed with status {status}; see {log}")


def tune(
    out: Path,
    model: str,
    start: Path,
    base: Path,
    settings: Settings,
    score: Callable[[Path], dict[str, float]],
    log: Callable[[str], None] = print,
) -> Path:
    """Trains `out/<model>.traineddata`'s network from `start` in rounds; returns the best model.

    `base` is the start model's traineddata. `score` takes a tessdata folder holding
    `<model>.traineddata` and returns a CER per dev set. Rounds already recorded in
    `rounds.json` are kept, so a rerun resumes after the last finished round.
    """
    work = tune_dir(out, settings)
    tessdata = work / "tessdata"
    tessdata.mkdir(parents=True, exist_ok=True)
    record = work / "rounds.json"
    rounds = [Round(**r) for r in json.loads(record.read_text())] if record.exists() else []
    checkpoint = work / f"{model}_checkpoint"
    output = work / "lstmtraining.log"
    rate = settings.learning_rate
    # --reset_learning_rate, else a model's stored rate wins over --learning_rate
    rate_args = () if rate is None else ("--learning_rate", str(rate), "--reset_learning_rate")
    while len(rounds) < settings.max_rounds and not should_stop(
        [r.dev_cer for r in rounds], settings.patience
    ):
        lines = (len(rounds) + 1) * settings.round_lines
        _lstmtraining(
            "--debug_interval", "0",
            "--traineddata", str(out / f"{model}.traineddata"),
            "--old_traineddata", str(base),
            "--continue_from", str(start),
            *rate_args,
            "--model_output", str(work / model),
            "--train_listfile", str(out / "list.train"),
            "--eval_listfile", str(out / "list.eval"),
            "--max_iterations", str(lines),
            "--target_error_rate", "0.001",
            "--max_image_MB", "1000",
            log=output,
        )  # fmt: skip
        _lstmtraining(
            "--stop_training",
            "--continue_from", str(checkpoint),
            "--traineddata", str(out / f"{model}.traineddata"),
            "--model_output", str(tessdata / f"{model}.traineddata"),
            log=output,
        )  # fmt: skip
        scores = score(tessdata)
        rounds.append(Round(lines, sum(scores.values()) / len(scores), scores))
        if best_round(rounds) == len(rounds) - 1:
            shutil.copy(checkpoint, work / f"{model}_best.checkpoint")
        for kept in work.glob(f"{model}_[0-9]*.checkpoint"):
            kept.unlink()  # lstmtraining's lowest-training-error copies, 24 MB each
        record.write_text(json.dumps([asdict(r) for r in rounds], indent=1) + "\n")
        log(f"round {len(rounds)}: {lines} lines, dev CER {rounds[-1].dev_cer:.4f} {scores}")
    best = rounds[best_round(rounds)]
    log(f"best: {best.lines} lines, dev CER {best.dev_cer:.4f}")
    final = work / f"{model}.traineddata"
    _lstmtraining(
        "--stop_training",
        "--continue_from", str(work / f"{model}_best.checkpoint"),
        "--traineddata", str(out / f"{model}.traineddata"),
        "--model_output", str(final),
        log=output,
    )  # fmt: skip
    return final
