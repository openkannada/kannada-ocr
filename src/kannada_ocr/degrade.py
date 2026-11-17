"""Makes clean renders look like scans of printed pages, including old letterpress.

Arrays are float32. `ink` is coverage in [0, 1] with 1 for full ink; a page image is
brightness in [0, 1] with 1 for white paper. Every random choice comes from the
`numpy.random.Generator` passed in, so a seed reproduces an image exactly.
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

PROFILES = ("clean", "print", "letterpress")
MIN_INK_KEPT = 0.6


def _to_image(a: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8))


def _from_image(im: Image.Image) -> np.ndarray:
    return np.asarray(im, dtype=np.float32) / 255.0


def blur(a: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return a
    return _from_image(_to_image(a).filter(ImageFilter.GaussianBlur(sigma)))


def smooth_noise(shape: tuple[int, int], cell: float, rng: np.random.Generator) -> np.ndarray:
    """Noise in [0, 1] that varies over about `cell` pixels."""
    h, w = shape
    grid = rng.random((max(2, int(h / cell) + 2), max(2, int(w / cell) + 2)), dtype=np.float32)
    return _from_image(_to_image(grid).resize((w, h), Image.Resampling.BICUBIC))


def _smoothstep(a: np.ndarray, center: float, width: float = 0.08) -> np.ndarray:
    t = np.clip((a - center + width) / (2 * width), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def stroke_weight(ink: np.ndarray, threshold: float, sigma: float) -> np.ndarray:
    """Blur then re-threshold. A threshold below 0.5 spreads ink; above 0.5 thins it."""
    return _smoothstep(blur(ink, sigma), threshold)


def break_strokes(
    ink: np.ndarray, rng: np.random.Generator, amount: float, cell: float
) -> np.ndarray:
    """Removes ink in small patches, as worn type and uneven pressure do."""
    holes = smooth_noise(ink.shape, cell, rng) < amount
    return ink * np.where(holes, rng.uniform(0.0, 0.3), 1.0).astype(np.float32)


def paper(
    shape: tuple[int, int], rng: np.random.Generator, tone: float, grain: float, stains: float
) -> np.ndarray:
    fibers = smooth_noise(shape, 1.5, rng) - 0.5
    blotches = smooth_noise(shape, max(shape) / 3, rng) - 0.5
    return np.clip(tone + grain * fibers + stains * blotches, 0.0, 1.0)


def rotate(page: np.ndarray, degrees: float, fill: float) -> np.ndarray:
    im = _to_image(page).rotate(
        degrees, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=int(fill * 255)
    )
    return _from_image(im)


def jpeg(page: np.ndarray, quality: int) -> np.ndarray:
    buffer = io.BytesIO()
    _to_image(page).save(buffer, format="JPEG", quality=quality)
    return _from_image(Image.open(buffer).convert("L"))


def wear(ink: np.ndarray, rng: np.random.Generator, params: dict[str, Any]) -> np.ndarray:
    """Letterpress ink: heavier or lighter strokes, broken patches, uneven density.

    If the strokes would lose more than `1 - MIN_INK_KEPT` of their ink, the weight
    change and breaks are skipped: thin display faces can vanish entirely, and an
    unreadable image would teach the model noise.
    """
    params["threshold"] = float(rng.uniform(0.3, 0.6))
    worn = stroke_weight(ink, params["threshold"], float(rng.uniform(0.4, 1.0)))
    params["breaks"] = float(rng.uniform(0.0, 0.25))
    worn = break_strokes(worn, rng, params["breaks"], float(rng.uniform(1.5, 4.0)))
    density = 0.75 + 0.25 * smooth_noise(ink.shape, ink.shape[0], rng)
    if (worn * density).sum() < MIN_INK_KEPT * ink.sum():
        worn, params["threshold"], params["breaks"] = ink, None, None
    return worn * density


def degrade(
    ink: np.ndarray,
    profile: str,
    rng: np.random.Generator,
    ghost: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """A grayscale page image for `ink`, and the parameters used.

    `ghost` is the ink of another line; letterpress pages show it mirrored, as
    text printed on the back of the sheet that bleeds through.
    """
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}")
    p: dict[str, Any] = {"profile": profile}
    heavy = profile == "letterpress"

    if heavy:
        ink = wear(ink, rng, p)

    shape = ink.shape
    tone = float(rng.uniform(0.70, 0.92) if heavy else rng.uniform(0.88, 1.0))
    page = paper(
        shape,
        rng,
        tone,
        grain=float(rng.uniform(0.04, 0.12) if heavy else rng.uniform(0.0, 0.03)),
        stains=float(rng.uniform(0.0, 0.15) if heavy else 0.0),
    )
    p["paper"] = round(tone, 3)

    if heavy and ghost is not None and rng.random() < 0.6:
        mirrored = np.fliplr(ghost)
        back = np.zeros(shape, dtype=np.float32)
        h, w = min(shape[0], mirrored.shape[0]), min(shape[1], mirrored.shape[1])
        back[:h, :w] = mirrored[:h, :w]
        p["bleed"] = float(rng.uniform(0.08, 0.25))
        page = page * (1.0 - p["bleed"] * blur(back, float(rng.uniform(1.0, 2.5))))

    darkness = float(rng.uniform(0.75, 0.95) if heavy else rng.uniform(0.85, 1.0))
    page = page * (1.0 - darkness * ink)

    max_skew = {"clean": 0.0, "print": 1.0, "letterpress": 2.5}[profile]
    if max_skew:
        p["skew"] = float(rng.uniform(-max_skew, max_skew))
        page = rotate(page, p["skew"], fill=tone)

    p["blur"] = float(rng.uniform(0.0, 1.2 if heavy else 0.6))
    page = blur(page, p["blur"])

    if profile != "clean" and rng.random() < 0.5:
        p["scale"] = float(rng.uniform(0.5, 0.9))
        im = _to_image(page)
        small = im.resize(
            (max(1, int(im.width * p["scale"])), max(1, int(im.height * p["scale"]))),
            Image.Resampling.BILINEAR,
        )
        page = _from_image(small.resize(im.size, Image.Resampling.BILINEAR))

    p["noise"] = float(rng.uniform(0.0, 0.05 if heavy else 0.02))
    page = page + rng.normal(0.0, p["noise"], page.shape).astype(np.float32)
    page = np.clip(page, 0.0, 1.0)

    if heavy and rng.random() < 0.15:
        p["binarized"] = True
        page = (page > (page.mean() - 0.1)).astype(np.float32)
    elif profile != "clean" and rng.random() < 0.5:
        p["jpeg"] = int(rng.integers(35, 90))
        page = jpeg(page, p["jpeg"])
    return page, p


def to_uint8(page: np.ndarray) -> np.ndarray:
    return np.clip(page * 255.0 + 0.5, 0, 255).astype(np.uint8)
