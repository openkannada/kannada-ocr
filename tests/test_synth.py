# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import io
import json

import pyarrow.parquet as pq
import pytest
from PIL import Image

from kannada_ocr.fonts import Font
from kannada_ocr.synth import Plan, generate, label_for, make_sample


def font(face, digit_style=None):
    return Font(face, face.family, "OFL-1.1", digit_style)


def test_labels_follow_the_digits_the_font_draws(noto):
    assert label_for(font(noto, "latin"), "ಕ್ರಿ.ಶ. ೧೯೨೦") == "ಕ್ರಿ.ಶ. 1920"
    assert label_for(font(noto, "kannada"), "ISO 9001") == "ISO ೯೦೦೧"
    assert label_for(font(noto), "೧೯೨೦ 1920") == "೧೯೨೦ 1920"


def test_samples_are_reproducible(noto):
    plan = Plan(lines=[("wikipedia", "ಕನ್ನಡ ನಾಡು ನುಡಿ")], fonts=[font(noto)], seed=5)
    a, b = make_sample(plan, 3), make_sample(plan, 3)
    assert a == b and a["text"] == "ಕನ್ನಡ ನಾಡು ನುಡಿ"
    assert json.loads(a["degradation"])["profile"] in ("clean", "print", "letterpress")


def test_profile_weights_choose_the_damage(noto):
    plan = Plan(lines=[("w", "ಕನ್ನಡ")], fonts=[font(noto)], seed=1, profile_weights=(0, 0, 1))
    profiles = {json.loads(make_sample(plan, i)["degradation"])["profile"] for i in range(20)}
    assert profiles == {"letterpress"}


def test_generate_writes_parquet_shards(tmp_path, noto):
    plan = Plan(lines=[("wikisource", "ಹಳೆಯ ಪುಸ್ತಕ")], fonts=[font(noto)], seed=0)
    summary = generate(plan, tmp_path, 5, workers=2, shard_size=2, log=lambda _: None)
    assert summary["samples"] == 5
    assert summary["shards"] == [f"train-0000{i}-of-00003.parquet" for i in range(3)]
    table = pq.read_table(tmp_path / "data" / summary["shards"][0])
    features = json.loads(table.schema.metadata[b"huggingface"])["info"]["features"]
    assert features["image"] == {"_type": "Image"}
    assert set(features) == set(table.column_names)
    rows = table.to_pylist()
    assert Image.open(io.BytesIO(rows[0]["image"]["bytes"])).mode == "L"


def test_more_than_4_workers_is_refused(tmp_path, noto):
    with pytest.raises(ValueError):
        generate(Plan([("wikipedia", "ಕ")], [font(noto)], 0), tmp_path, 0, workers=5)


def test_a_second_run_into_the_same_directory_is_refused(tmp_path, noto):
    plan = Plan(lines=[("wikisource", "ಹಳೆಯ ಪುಸ್ತಕ")], fonts=[font(noto)], seed=0)
    generate(plan, tmp_path / "run", 2, workers=1, log=lambda _: None)
    with pytest.raises(FileExistsError):
        generate(plan, tmp_path / "run", 1, workers=1, log=lambda _: None)


def test_generation_stops_at_the_size_limit_across_runs(tmp_path, noto):
    plan = Plan(lines=[("wikisource", "ಹಳೆಯ ಪುಸ್ತಕ")], fonts=[font(noto)], seed=0)
    (tmp_path / "older").mkdir()
    (tmp_path / "older" / "big.bin").write_bytes(b"x" * 1000)
    summary = generate(
        plan, tmp_path / "run", 6, workers=1, shard_size=2, max_bytes=1500, log=lambda _: None
    )
    assert summary["stopped_early"] == "generated data reached its size limit"
    assert summary["samples"] == 2 and len(summary["shards"]) == 1


def test_generation_writes_nothing_when_the_disk_is_nearly_full(tmp_path, noto, monkeypatch):
    import kannada_ocr.synth as synth

    monkeypatch.setattr(synth.shutil, "disk_usage", lambda _: type("U", (), {"free": 0})())
    plan = Plan(lines=[("wikisource", "ಹಳೆಯ ಪುಸ್ತಕ")], fonts=[font(noto)], seed=0)
    summary = generate(plan, tmp_path / "run", 4, workers=1, shard_size=2, log=lambda _: None)
    assert summary["samples"] == 0 and summary["shards"] == []
    assert summary["stopped_early"].startswith("not written")


def legacy(name, digit_style):
    from conftest import font_or_skip

    face = font_or_skip("nudi", f"{name}.ttf")
    return Font(face, "legacy-" + name, "KaGaPa free download", digit_style, "nudi")


def test_legacy_fonts_render_glyph_codes_with_a_unicode_label():
    from kannada_ocr import text

    lines = [("wikisource", "ಕನ್ನಡ ನಾಡು ೧೯೨೦")]
    plan = Plan(lines, [legacy("Nudi 01 e", "latin")], 0, tuple(text.to_nudi([lines[0][1]])))
    sample = make_sample(plan, 1)
    assert sample["text"] == "ಕನ್ನಡ ನಾಡು 1920" and sample["font_encoding"] == "nudi"


def test_a_line_kannadi_cannot_encode_is_not_set_in_a_legacy_font():
    lines = [("wikipedia", "ಕನ್ನಡ ISO")]
    plan = Plan(lines, [legacy("Nudi 01 k", "kannada")], 0, (None,))
    assert make_sample(plan, 0) is None
