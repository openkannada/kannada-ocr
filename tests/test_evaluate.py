# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import pytest
from PIL import Image

from kannada_ocr.dataset import ImageFolderWriter, read_jsonl
from kannada_ocr.evaluate import evaluate, select


class Echo:
    """Returns the reference text, except for item b, which it reads with 1 wrong letter."""

    name = "echo"
    workers = 2
    config = "echo v1"

    def __init__(self, texts):
        self.texts = texts
        self.calls = 0

    def recognize(self, image, level):
        self.calls += 1
        text = self.texts[image.stem]
        return text.replace("ಕ", "ಖ") if image.stem == "b" else text


def make_bench(root):
    texts = {"a": "ಕನ್ನಡ ನಾಡು", "b": "ಕನ್ನಡ", "c": "ಹಳ್ಳಿ"}
    with ImageFolderWriter(root) as w:
        for key, text in texts.items():
            w.add(key, Image.new("L", (8, 4), 255), text, level="line", group=key, split="test")
    return texts


def test_a_transform_changes_scoring_and_the_file_name(tmp_path):
    bench = tmp_path / "set"
    model = Echo(make_bench(bench))

    def undo_b(hyp):
        return hyp.replace("ಖ", "ಕ")

    summary = evaluate(model, bench, tmp_path / "r", log=lambda _: None, transform=undo_b)
    assert summary["chars"]["edits"] == 0 and summary["transform"] == "undo_b"
    assert (tmp_path / "r" / "echo" / "set.test.undo_b.json").exists()


def test_select_takes_a_fixed_sample():
    rows = [{"id": str(i), "split": "test"} for i in range(50)]
    first = select(rows, "test", 10)
    assert first == select(list(reversed(rows)), "test", 10)
    assert len(first) == 10 and select(rows, "dev", None) == []


def test_evaluate_scores_and_resumes(tmp_path):
    bench = tmp_path / "set"
    texts = make_bench(bench)
    model = Echo(texts)
    summary = evaluate(model, bench, tmp_path / "results", log=lambda _: None)
    assert summary["items"] == 3 and summary["chars"]["edits"] == 1
    assert summary["wrong_script_items"] == 0
    assert summary["cer_by_group"] == {"a": 0.0, "b": 0.2, "c": 0.0}
    assert len(read_jsonl(tmp_path / "results" / "echo" / "set.predictions.jsonl")) == 3
    evaluate(model, bench, tmp_path / "results", log=lambda _: None)
    assert model.calls == 3


def test_predictions_are_redone_when_the_config_or_image_changes(tmp_path):
    bench = tmp_path / "set"
    model = Echo(make_bench(bench))
    evaluate(model, bench, tmp_path / "r", log=lambda _: None)
    model.config = "echo v2"
    evaluate(model, bench, tmp_path / "r", log=lambda _: None)
    assert model.calls == 6
    Image.new("L", (8, 4), 0).save(bench / "images" / "a.png")
    evaluate(model, bench, tmp_path / "r", log=lambda _: None)
    assert model.calls == 7


def test_a_torn_last_prediction_line_is_redone(tmp_path):
    bench = tmp_path / "set"
    model = Echo(make_bench(bench))
    evaluate(model, bench, tmp_path / "r", log=lambda _: None)
    path = tmp_path / "r" / "echo" / "set.predictions.jsonl"
    path.write_text(path.read_text()[:-20])
    summary = evaluate(model, bench, tmp_path / "r", log=lambda _: None)
    assert model.calls == 4 and summary["chars"]["edits"] == 1


def test_an_empty_selection_is_refused(tmp_path):
    bench = tmp_path / "set"
    make_bench(bench)
    with pytest.raises(ValueError):
        evaluate(Echo({}), bench, tmp_path / "r", split="dev", log=lambda _: None)
