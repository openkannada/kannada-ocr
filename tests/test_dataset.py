import json

import pytest
from PIL import Image

from kannada_ocr.dataset import ImageFolderWriter, assign_splits, read_jsonl


def test_splits_are_stable_and_keep_whole_groups():
    groups = {f"book{i}" for i in range(32)}
    first = assign_splits(groups)
    assert first == assign_splits(set(sorted(groups, reverse=True)))
    assert sum(v == "dev" for v in first.values()) == 6


def test_a_small_set_still_gets_a_dev_group():
    assert sorted(assign_splits({"a", "b"}).values()) == ["dev", "test"]
    assert assign_splits(set()) == {}


def test_writer_saves_images_and_metadata_with_splits(tmp_path):
    with ImageFolderWriter(tmp_path) as w:
        w.add("x1", Image.new("L", (4, 2), 255), "ಕ", group="g1")
        w.add("x2", Image.new("L", (4, 2), 255), "ಖ", group="g1", split="test")
    rows = read_jsonl(tmp_path / "metadata.jsonl")
    assert [r["file_name"] for r in rows] == ["images/x1.png", "images/x2.png"]
    assert rows[0]["split"] == "dev" and rows[1]["split"] == "test"
    assert (tmp_path / "images" / "x1.png").exists()


def test_a_torn_last_line_is_dropped_only_when_allowed(tmp_path):
    path = tmp_path / "p.jsonl"
    path.write_text(json.dumps({"id": "a"}) + "\n" + '{"id": "b", "hy')
    assert read_jsonl(path, allow_torn_tail=True) == [{"id": "a"}]
    with pytest.raises(json.JSONDecodeError):
        read_jsonl(path)
    path.write_text('{"id": "b", "hy\n' + json.dumps({"id": "a"}) + "\n")
    with pytest.raises(json.JSONDecodeError):
        read_jsonl(path, allow_torn_tail=True)
