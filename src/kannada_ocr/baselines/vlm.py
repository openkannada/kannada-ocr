"""Vision-language OCR models run locally on Apple Silicon with mlx-vlm."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from PIL import Image

PROMPTS = {"paddleocr-vl": "OCR:"}
"""Task prompts from the model cards. The default is the plain OCR prompt of dots.ocr."""
DEFAULT_PROMPT = "Extract the text content from this image."

MAX_TOKENS = {"word": 64, "line": 256, "page": 3072}
MIN_HEIGHT = 96
"""Word crops are about 50 pixels tall; models return nothing for many unless enlarged."""


class VLM:
    """Loads the model on first use, so rescoring saved predictions needs no model."""

    workers = 1

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.name = model_id.split("/")[-1]
        key = self.name.lower()
        self.prompt = next((p for k, p in PROMPTS.items() if k in key), DEFAULT_PROMPT)
        self.config = (
            f"{model_id} prompt {self.prompt!r} min height {MIN_HEIGHT} max tokens {MAX_TOKENS}"
            f" markup {MARKUP_VERSION}"
        )
        self._loaded: tuple | None = None
        self._lock = threading.Lock()

    def _load(self) -> tuple:
        if self._loaded is None:
            from mlx_vlm import load
            from mlx_vlm.prompt_utils import apply_chat_template

            model, processor = load(self.model_id)
            template = apply_chat_template(processor, model.config, self.prompt, num_images=1)
            self._loaded = (model, processor, template)
        return self._loaded

    def recognize(self, image: Path, level: str) -> str:
        from mlx_vlm import generate

        with self._lock, tempfile.TemporaryDirectory() as tmp:
            model, processor, prompt = self._load()
            result = generate(
                model,
                processor,
                prompt,
                [str(enlarged(image, Path(tmp)))],
                max_tokens=MAX_TOKENS[level],
                temperature=0.0,
                verbose=False,
            )
        return strip_markup(result.text)


def enlarged(image: Path, tmp: Path) -> Path:
    """`image`, or a copy scaled up to `MIN_HEIGHT` pixels tall if it is shorter."""
    with Image.open(image) as im:
        if im.height >= MIN_HEIGHT:
            return image
        scale = MIN_HEIGHT / im.height
        big = im.resize((round(im.width * scale), MIN_HEIGHT), Image.Resampling.LANCZOS)
    path = tmp / "enlarged.png"
    big.save(path)
    return path


MARKUP_VERSION = 1
"""Bump when `strip_markup` changes, so saved predictions are redone."""


def strip_markup(text: str) -> str:
    """Drops the code fences and end tokens some OCR models wrap around plain text."""
    text = text.strip()
    for token in ("<|endoftext|>", "<|im_end|>", "</s>"):
        text = text.replace(token, "")
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()
