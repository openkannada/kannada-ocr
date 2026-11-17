# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Renders a line of text with HarfBuzz shaping and FreeType rasterizing.

Pillow's wheels are built without libraqm, so `ImageDraw.text` cannot form Kannada
conjuncts. HarfBuzz does the shaping here, so every glyph is the one a reader would see.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import freetype
import numpy as np
import uharfbuzz as hb

PROBE = "ಕ್ಷ"
"""ಕ + ್ + ಷ (U+0C95 U+0CCD U+0CB7) shapes to 1 conjunct glyph in any working Kannada font."""


@dataclass(frozen=True)
class FontFace:
    path: Path
    family: str
    weight: int | None = None
    """A `wght` axis value for variable fonts; None for static fonts."""

    @property
    def name(self) -> str:
        return f"{self.family}" + (f" {self.weight}" if self.weight else "")


@dataclass
class _Loaded:
    hb_font: hb.Font
    ft_face: freetype.Face
    upem: int
    size: int = 0
    glyphs: dict[int, tuple[np.ndarray, int, int]] = field(default_factory=dict)


@cache
def _load(face: FontFace) -> _Loaded:
    blob = hb.Blob.from_file_path(str(face.path))
    hb_face = hb.Face(blob)
    font = hb.Font(hb_face)
    ft = freetype.Face(str(face.path))
    if face.weight is not None:
        font.set_variations({"wght": face.weight})
        axes = ft.get_variation_info().axes
        ft.set_var_design_coords([face.weight if a.tag == "wght" else a.default for a in axes])
    return _Loaded(hb_font=font, ft_face=ft, upem=hb_face.upem)


def _shape(face: FontFace, text: str) -> tuple[list[int], list[tuple[int, int, int]], list[int]]:
    loaded = _load(face)
    buf = hb.Buffer()
    buf.add_codepoints([ord(c) for c in text])
    buf.guess_segment_properties()
    hb.shape(loaded.hb_font, buf, {})
    ids = [info.codepoint for info in buf.glyph_infos]
    clusters = [info.cluster for info in buf.glyph_infos]
    moves = [(p.x_advance, p.x_offset, p.y_offset) for p in buf.glyph_positions]
    return ids, moves, clusters


def shape(face: FontFace, text: str) -> tuple[list[int], list[tuple[int, int, int]]]:
    """Glyph ids and (x_advance, x_offset, y_offset) in font units."""
    ids, moves, _ = _shape(face, text)
    return ids, moves


def _needs_ink(c: str) -> bool:
    """Characters outside the Kannada block that must show ink: digits, Latin, punctuation.

    Kannada marks may legitimately shape to blank component glyphs, so they are not checked.
    """
    return not c.isspace() and not ("\u0c80" <= c <= "\u0cff") and c not in "\u200c\u200d"


def _cluster_starts(text: str, clusters: list[int]) -> list[tuple[int, str]]:
    """(cluster, character) for each character that starts a cluster."""
    starts = set(clusters)
    return [(i, c) for i, c in enumerate(text) if i in starts]


def covers(face: FontFace, text: str) -> bool:
    """True when every character shapes to a real glyph (none is .notdef)."""
    ids, _ = shape(face, text)
    return all(ids)


def shapes_kannada(face: FontFace) -> bool:
    """True when the font has Kannada glyphs and forms conjuncts.

    Legacy fonts such as Nudi 01 put glyphs on Latin code points, and some old
    Unicode fonts lack the OpenType tables; both fail this check.
    """
    ids, _ = shape(face, PROBE)
    return all(ids) and len(ids) < len(PROBE)


def _glyph(loaded: _Loaded, glyph_id: int) -> tuple[np.ndarray, int, int]:
    if glyph_id not in loaded.glyphs:
        ft = loaded.ft_face
        ft.load_glyph(glyph_id, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_LIGHT)
        slot = ft.glyph
        bm = slot.bitmap
        array = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.pitch)[:, : bm.width]
        loaded.glyphs[glyph_id] = (array, slot.bitmap_left, slot.bitmap_top)
    return loaded.glyphs[glyph_id]


def render(face: FontFace, text: str, size: int, pad: int = 4) -> np.ndarray | None:
    """Ink coverage in [0, 1] as float32, cropped to the ink plus `pad` pixels.

    `size` is the em size in pixels. Returns None if the font lacks a glyph, or draws
    a digit, letter or punctuation mark outside the Kannada block as a blank.
    """
    ids, moves, clusters = _shape(face, text)
    if not all(ids):
        return None
    loaded = _load(face)
    if loaded.size != size:
        loaded.ft_face.set_pixel_sizes(0, size)
        loaded.size, loaded.glyphs = size, {}
    scale = size / loaded.upem
    width = int(sum(m[0] for m in moves) * scale) + 4 * size
    height = 4 * size
    baseline = 2 * size + size // 2
    canvas = np.zeros((height, width), dtype=np.float32)
    pen = 2 * size * 1.0
    inked: set[int] = set()
    for glyph_id, (advance, x_offset, y_offset), cluster in zip(ids, moves, clusters, strict=True):
        bitmap, left, top = _glyph(loaded, glyph_id)
        if bitmap.any():
            inked.add(cluster)
        x = int(round(pen + x_offset * scale)) + left
        y = baseline - int(round(y_offset * scale)) - top
        h, w = bitmap.shape
        if h and w:
            if x < 0 or x + w > width or y < 0 or y + h > height:
                return None
            region = canvas[y : y + h, x : x + w]
            np.maximum(region, bitmap / 255.0, out=region)
        pen += advance * scale
    if any(_needs_ink(c) and i not in inked for i, c in _cluster_starts(text, clusters)):
        return None
    rows = np.flatnonzero(canvas.max(axis=1) > 0.05)
    cols = np.flatnonzero(canvas.max(axis=0) > 0.05)
    if not len(rows):
        return None
    return np.pad(canvas[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1], pad, constant_values=0.0)
