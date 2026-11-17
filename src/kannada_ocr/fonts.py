# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""The font inventory for synthetic rendering, built from `fonts.json` and `data/fonts`."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .http import Client
from .render import FontFace, covers, render, shapes_kannada

SAME_WIDTH = 1.2
"""Distinct digit sets have ೧ at least 1.3 times as wide as 1; shared styles are within 1.1."""
NARROW_ONE = 0.7
"""Width over height of 1: about 0.3 to 0.6 in Latin designs, 0.8 to 1.2 in Kannada ones."""
OFL = "OFL-1.1"
KAGAPA = "KaGaPa free download"
"""The Nudi archive has no license text; these fonts are a free download from KaGaPa."""
CATALOG = Path(__file__).resolve().parents[2] / "fonts.json"


@dataclass(frozen=True)
class Font:
    face: FontFace
    design: str
    """Files of 1 design share this key, so sampling by design does not favor big families."""
    license: str
    digit_style: str | None
    """"latin" or "kannada" when the font draws both digit sets (0-9 and U+0CE6 to U+0CEF)
    with the same glyphs, in that style; None when they look different."""
    encoding: str = "unicode"
    """"unicode", or "nudi" for legacy fonts that take Nudi and Baraha ANSI glyph codes."""


def design_key(stem: str) -> str:
    """`NUDI UNI 01E BOLD` and `NudiUni01e` both give `nudiuni01`."""
    key = re.sub(r"[\s_\-]+", "", stem.lower())
    key = re.sub(r"\[.*\]", "", key)
    key = re.sub(r"(bold|italic|regular|light)$", "", key)
    return re.sub(r"(?<=\d)[ek]$", "", key)


def _aspect(face: FontFace, glyph: str) -> float | None:
    ink = render(face, glyph, 48, pad=0)
    return None if ink is None else ink.shape[1] / ink.shape[0]


def digit_style(face: FontFace) -> str | None:
    """How a font draws digits, when it draws 1 and ೧ in the same style.

    Nudi "E" fonts draw Kannada digits as Latin ones and "K" fonts the reverse.
    A Latin 1 is a narrow stroke and a Kannada ೧ is about as wide as it is tall,
    so 2 glyphs of similar width share a style, and that width tells which.
    """
    latin, kannada = _aspect(face, "1"), _aspect(face, "೧")
    if latin is None or kannada is None or not 1 / SAME_WIDTH <= kannada / latin <= SAME_WIDTH:
        return None
    return "latin" if latin < NARROW_ONE else "kannada"


NUDI_PROBE = "PÀ£ÀßqÀ ²æÃgÁªÀÄ"
"""ಕನ್ನಡ ಶ್ರೀರಾಮ in Nudi glyph codes, from kannadi's encoder."""


def legacy_digit_style(face: FontFace) -> str | None:
    """Digits in a legacy font: kannadi writes every digit as ASCII, and Nudi "e" fonts
    draw them as Latin digits while "k" fonts draw them as Kannada ones."""
    one = _aspect(face, "1")
    if one is None:
        return None
    return "latin" if one < NARROW_ONE else "kannada"


def legacy_inventory(fonts_dir: Path, catalog: Path = CATALOG, log=print) -> list[Font]:
    """Legacy Nudi fonts: no Kannada code points, a glyph for every probe code, and not
    excluded in `fonts.json` after a visual check. Exclusions are by file, since design
    keys merge files such as NUDI-04 and Nudi 04 e that are different designs."""
    spec = json.loads(catalog.read_text())
    excluded = set(spec["nudi"]["legacy_exclude"]["files"])
    fonts = []
    for path in sorted((fonts_dir / "nudi").glob("*")):
        face = FontFace(path, path.stem)
        if path.suffix.lower() != ".ttf" or path.stem in excluded:
            continue
        if covers(face, "ಕ") or not covers(face, NUDI_PROBE):
            continue
        fonts.append(
            Font(
                face,
                "legacy-" + design_key(path.stem),
                KAGAPA,
                legacy_digit_style(face),
                "nudi",
            )
        )
    log(f"{len(fonts)} legacy fonts in {len({f.design for f in fonts})} designs")
    return fonts


def download(
    client: Client, fonts_dir: Path, catalog: Path = CATALOG, kagapa: bool = False
) -> None:
    """Downloads the OFL fonts, and with `kagapa` the KaGaPa Nudi archive, which has no license."""
    spec = json.loads(catalog.read_text())
    for family in spec["google"]:
        for url in family["files"]:
            name = urllib.parse.unquote(url.rsplit("/", 1)[1])
            quoted = url.replace("[", "%5B").replace("]", "%5D").replace(",", "%2C")
            client.download(quoted, fonts_dir / "google" / name)
    if not kagapa:
        return
    archive = client.download(spec["nudi"]["archive"], fonts_dir / "kagapa-zip" / "Fonts.zip")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != spec["nudi"]["sha256"]:
        archive.unlink()  # else the client's cache returns the same bad file on every rerun
        raise ValueError(
            f"{archive} does not match the SHA-256 in {catalog.name}; rerun to fetch it"
        )
    nudi = fonts_dir / "nudi"
    nudi.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = Path(info.filename).name
            if name.lower().endswith(".ttf") and not (nudi / name).exists():
                (nudi / name).write_bytes(z.read(info))


def inventory(fonts_dir: Path, catalog: Path = CATALOG, log=print) -> list[Font]:
    """Every font that shapes Kannada correctly, with variable fonts expanded to their weights."""
    spec = json.loads(catalog.read_text())
    excluded = set(spec["nudi"]["exclude"]["designs"])
    weights = {
        urllib.parse.unquote(url.rsplit("/", 1)[1]): fam["weights"]
        for fam in spec["google"]
        for url in fam["files"]
    }
    faces: list[tuple[FontFace, str]] = []
    for path in sorted((fonts_dir / "google").glob("*.ttf")):
        for weight in weights.get(path.name) or [None]:
            faces.append((FontFace(path, path.stem, weight), OFL))
    for path in sorted((fonts_dir / "nudi").glob("*")):
        if path.suffix.lower() == ".ttf" and design_key(path.stem) not in excluded:
            faces.append((FontFace(path, path.stem), KAGAPA))
    fonts = []
    for face, license_name in faces:
        if not shapes_kannada(face):
            continue
        fonts.append(Font(face, design_key(face.family), license_name, digit_style(face)))
    log(f"{len(fonts)} usable fonts in {len({f.design for f in fonts})} designs")
    return fonts
