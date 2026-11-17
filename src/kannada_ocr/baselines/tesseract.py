"""Tesseract 5 with the `kan` model from tessdata_best, or a model fine-tuned from it."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

PAGE_SEGMENTATION = {"word": 8, "line": 7, "page": 3}
"""Mode 3 finds columns. Mode 4, used by the Lipi Gnani evaluation, reads straight across
2-column pages, which the references list column by column, but copes better with drop
capitals and ornaments in old print. Both are reported."""


class Tesseract:
    workers = 2

    def __init__(self, tessdata: Path, lang: str = "kan", page_mode: int = 3) -> None:
        if not (tessdata / f"{lang}.traineddata").exists():
            raise FileNotFoundError(f"{tessdata}/{lang}.traineddata is missing")
        self.tessdata = tessdata
        self.lang = lang
        self.page_mode = page_mode
        suffix = "" if page_mode == PAGE_SEGMENTATION["page"] else f"-psm{page_mode}"
        version = self.version()
        best = "-best" if lang == "kan" else ""
        self.name = f"tesseract-{version}-{lang}{best}{suffix}"
        model = hashlib.sha256((tessdata / f"{lang}.traineddata").read_bytes()).hexdigest()[:16]
        self.config = (
            f"tesseract {version} {lang} {model} oem 1 psm {PAGE_SEGMENTATION} page {page_mode}"
        )

    @staticmethod
    def version() -> str:
        out = subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout
        return out.split()[1]

    def recognize(self, image: Path, level: str) -> str:
        env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
        result = subprocess.run(
            [
                "tesseract",
                str(image),
                "stdout",
                "--tessdata-dir",
                str(self.tessdata),
                "-l",
                self.lang,
                "--oem",
                "1",
                "--psm",
                str(self.page_mode if level == "page" else PAGE_SEGMENTATION[level]),
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"tesseract failed on {image}: {result.stderr.strip()}")
        return result.stdout.replace("\f", "").strip()
