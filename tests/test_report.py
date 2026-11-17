# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import json

from kannada_ocr.report import by_book, table


def summary(model, set_name, items, sampled_from, transform=None, split="test"):
    return {
        "split": split,
        "model": model,
        "set": set_name,
        "items": items,
        "sampled_from": sampled_from,
        "transform": transform,
        "cer": 0.0123,
        "wer": 0.1,
        "aer": 0.02,
        "seconds_per_item": 1.5,
        "wrong_script_items": items // 10,
    }


def test_table_orders_sets_and_marks_samples_and_transforms(tmp_path):
    for i, s in enumerate(
        [
            summary("b", "wikisource-old", 60, 144),
            summary("a", "mile-lines", 6295, 6295),
            summary("b", "mile-lines", 600, 6295, transform="telugu_as_kannada"),
            summary("c", "degraded-words", 0, 0),
        ]
    ):
        (tmp_path / s["model"]).mkdir(exist_ok=True)
        (tmp_path / s["model"] / f"{i}.json").write_text(json.dumps(s))
    rows = table(tmp_path).splitlines()[2:]
    assert rows[0].startswith("| mile-lines | 6295 | a | 1.2% | 10.0% | 2.0% | 10.0% | 1.50 |")
    assert rows[1].startswith("| mile-lines | 600 of 6295 | b (telugu_as_kannada) |")
    assert rows[2].startswith("| wikisource-old | 60 of 144 | b |")
    assert len(rows) == 3


def test_table_shows_only_the_chosen_split(tmp_path):
    for s in [
        summary("a", "mile-lines", 600, 6295),
        summary("b", "mile-lines", 600, 700, split="dev"),
    ]:
        (tmp_path / s["model"]).mkdir()
        (tmp_path / s["model"] / "mile-lines.json").write_text(json.dumps(s))
    assert [r.split(" | ")[2] for r in table(tmp_path).splitlines()[2:]] == ["a"]
    assert [r.split(" | ")[2] for r in table(tmp_path, "dev").splitlines()[2:]] == ["b"]


def test_by_book_compares_models_on_their_shared_sample(tmp_path):
    def scored(model, items, groups, transform=None):
        s = summary(model, "wikisource-old", items, 144, transform)
        s["cer_by_group"] = groups
        (tmp_path / model).mkdir(exist_ok=True)
        name = f"wikisource-old.test.n{items}{'.' + transform if transform else ''}.json"
        (tmp_path / model / name).write_text(json.dumps(s))

    scored("a", 60, {"B1": 0.05, "B2": 0.2})
    scored("b", 60, {"B1": 0.07, "B2": 0.1})
    scored("b", 60, {"B1": 0.01, "B2": 0.01}, transform="x")
    scored("a", 144, {"B1": 0.01, "B2": 0.01, "B3": 0.01})
    rows = by_book(tmp_path, "wikisource-old").splitlines()
    assert rows[0] == "| Book | a | b |"
    assert rows[2:] == ["| B1 | **5.0%** | 7.0% |", "| B2 | 20.0% | **10.0%** |"]
