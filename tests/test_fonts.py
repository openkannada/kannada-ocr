# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import hashlib
import io
import json
import zipfile

import pytest

from kannada_ocr import cli, fonts


class FakeClient:
    def __init__(self, archive: bytes):
        self.archive = archive
        self.urls = []

    def download(self, url, dest):
        self.urls.append(url)
        if dest.exists():
            return dest  # as Client.download does
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.archive if url.endswith(".zip") else b"font")
        return dest


def catalog(tmp_path, archive: bytes):
    spec = {
        "google": [{"files": ["https://example.org/ofl/Sample.ttf"]}],
        "nudi": {"archive": "http://example.org/Fonts.zip", "sha256": "0" * 64},
    }
    spec["nudi"]["sha256"] = hashlib.sha256(archive).hexdigest()
    path = tmp_path / "fonts.json"
    path.write_text(json.dumps(spec))
    return path


def zipped(name: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(f"Fonts/{name}", b"nudi")
    return buffer.getvalue()


def test_only_ofl_fonts_are_downloaded_by_default(tmp_path):
    client = FakeClient(zipped("Nudi.ttf"))
    fonts.download(client, tmp_path / "fonts", catalog(tmp_path, client.archive))
    assert client.urls == ["https://example.org/ofl/Sample.ttf"]
    assert not (tmp_path / "fonts" / "nudi").exists()


def test_the_kagapa_archive_is_extracted_only_when_its_hash_matches(tmp_path):
    client = FakeClient(zipped("Nudi.ttf"))
    spec = catalog(tmp_path, client.archive)
    fonts.download(client, tmp_path / "fonts", spec, kagapa=True)
    assert (tmp_path / "fonts" / "nudi" / "Nudi.ttf").read_bytes() == b"nudi"

    other = FakeClient(b"<html>parked domain</html>")
    with pytest.raises(ValueError, match="SHA-256"):
        fonts.download(other, tmp_path / "other", spec, kagapa=True)
    assert not (tmp_path / "other" / "nudi").exists()

    other.archive = client.archive
    fonts.download(other, tmp_path / "other", spec, kagapa=True)
    assert (tmp_path / "other" / "nudi" / "Nudi.ttf").exists()


def test_the_defaults_follow_the_released_models_recipe(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "cmd_synth", lambda args: seen.update(fonts=args.fonts))
    monkeypatch.setattr(
        cli,
        "cmd_tesstrain_gt",
        lambda args: seen.update(gt=(args.model, args.kagapa, args.lines, args.synth)),
    )
    monkeypatch.setattr(
        cli, "cmd_tesstune", lambda args: seen.update(tune=(args.model, args.learning_rate))
    )
    monkeypatch.setattr(cli, "cmd_tesstrain_pack", lambda args: seen.update(pack=args.model))
    for command in ("synth", "tesstrain-gt", "tesstune", "tesstrain-pack"):
        cli.main([command])
    assert seen == {
        "fonts": "ofl",
        "gt": ("kan_ft_ofl3", 0, "wikisource-lines-120", ["synth-v0", "synth-v1-ofl"]),
        "tune": ("kan_ft_ofl3", None),
        "pack": "kan_ft_ofl3",
    }


def test_nudi_font_sets_need_the_kagapa_download(tmp_path):
    with pytest.raises(SystemExit, match="kocr fonts --kagapa"):
        cli.main(["--data", str(tmp_path), "synth", "--fonts", "legacy"])
