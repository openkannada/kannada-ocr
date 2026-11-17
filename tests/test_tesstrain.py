import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from PIL import Image

from kannada_ocr.tesstrain import Source, export, items


def png_bytes(shade):
    import io

    buffer = io.BytesIO()
    Image.new("L", (20, 10), shade).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def folder(tmp_path):
    root = tmp_path / "set"
    (root / "images").mkdir(parents=True)
    rows = []
    for i, split in enumerate(["train", "dev", "train", "train"]):
        Image.new("L", (20, 10), i).save(root / "images" / f"x{i}.png")
        rows.append(
            {"file_name": f"images/x{i}.png", "id": f"x{i}", "text": f"ಕನ್ನಡ  {i}", "split": split}
        )
    (root / "metadata.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return root


@pytest.fixture
def shards(tmp_path):
    root = tmp_path / "synth"
    (root / "data").mkdir(parents=True)
    for s in range(2):
        rows = [
            {
                "image": {"bytes": png_bytes(s * 10 + i), "path": None},
                "text": f"ಲೇಖ {s}{i}",
                "font_license": "OFL-1.1" if i < 2 else "other",
            }
            for i in range(3)
        ]
        pq.write_table(pa.Table.from_pylist(rows), root / "data" / f"train-{s:05d}.parquet")
    return root


def test_imagefolder_items_follow_the_split(folder):
    assert sorted(i for i, _, _ in items(Source("a", folder, split="train"))) == ["x0", "x2", "x3"]


def test_samples_are_a_hash_ranking_across_shards(shards):
    import hashlib

    every = [f"train-{s:05d}_{i:05d}" for s in range(2) for i in range(3)]
    ranked = sorted(every, key=lambda i: hashlib.sha256(i.encode()).hexdigest())
    assert [i for i, _, _ in items(Source("s", shards, count=4))] == ranked[:4]


def test_samples_are_fixed_and_nested(shards):
    three = [i for i, _, _ in items(Source("s", shards, count=3))]
    assert three == [i for i, _, _ in items(Source("s", shards, count=3))]
    assert three[:2] == [i for i, _, _ in items(Source("s", shards, count=2))]
    assert len({i for i, _, _ in items(Source("s", shards))}) == 6


def test_synthetic_items_can_be_limited_to_1_font_license(shards):
    chosen = sorted(i for i, _, _ in items(Source("s", shards, font_license="OFL-1.1")))
    assert chosen == [
        "train-00000_00000",
        "train-00000_00001",
        "train-00001_00000",
        "train-00001_00001",
    ]


def test_parquet_items_keep_each_image_with_its_label(shards):
    for item_id, png, label in items(Source("s", shards)):
        shard, row = item_id.split("_")
        shade = int(shard.removeprefix("train-")) * 10 + int(row)
        assert Image.open(__import__("io").BytesIO(png)).getpixel((0, 0)) == shade
        assert label == f"ಲೇಖ {shade // 10}{shade % 10}"


def test_export_writes_normalized_labels_and_a_manifest(folder, tmp_path):
    gt = tmp_path / "out" / "m-ground-truth"
    counts = export([Source("a", folder, split="dev")], gt)
    assert counts == {"a": 1}
    assert (gt / "a_x1.gt.txt").read_text(encoding="utf-8") == "ಕನ್ನಡ 1\n"
    assert (gt / "a_x1.png").exists()
    assert json.loads((tmp_path / "out" / "m-ground-truth.json").read_text())["lines"] == {"a": 1}


def test_export_links_grayscale_png_lines_and_reencodes_others(folder, tmp_path):
    Image.new("RGB", (20, 10), "white").save(folder / "images" / "x3.png")
    gt = tmp_path / "gt"
    export([Source("a", folder, split="train")], gt)
    assert (gt / "a_x0.png").stat().st_ino == (folder / "images" / "x0.png").stat().st_ino
    assert (gt / "a_x3.png").stat().st_ino != (folder / "images" / "x3.png").stat().st_ino
    assert Image.open(gt / "a_x3.png").mode == "L"


def test_export_drops_labels_with_letters_of_another_script(folder, tmp_path):
    rows = [json.loads(line) for line in (folder / "metadata.jsonl").read_text().splitlines()]
    rows[0]["text"] = "ಸ್ವಾಮಿజిಯ ಬಳಿಗೆ"
    (folder / "metadata.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    gt = tmp_path / "gt"
    assert export([Source("a", folder, split="train")], gt) == {"a": 2}
    assert not (gt / "a_x0.gt.txt").exists()


def test_export_refuses_to_mix_with_an_earlier_export(folder, tmp_path):
    gt = tmp_path / "gt"
    export([Source("a", folder)], gt)
    with pytest.raises(FileExistsError):
        export([Source("a", folder)], gt)


def test_box_lines_match_tesstrain_wordstr_format():
    from kannada_ocr.tesstrain import wordstr_box

    assert (
        wordstr_box(" ಕನ್ನಡ ನಾಡು ", 120, 30) == "WordStr 0 0 120 30 0 #ಕನ್ನಡ ನಾಡು\n\t 0 0 120 30 0\n"
    )
    assert wordstr_box("ಕನ್ನಡ", 9, 8, page=3).endswith("\t 0 0 9 8 3\n")
    with pytest.raises(ValueError):
        wordstr_box("שלום", 10, 10)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_pack_writes_1_lstmf_per_chunk_and_keeps_them_on_rerun(tmp_path):
    from kannada_ocr.tesstrain import pack

    gt = tmp_path / "gt"
    gt.mkdir()
    for i in range(3):
        image = Image.new("L", (60, 20), 255)
        image.paste(0, (10, 5, 50, 15))
        image.save(gt / f"a_{i}.png")
        (gt / f"a_{i}.gt.txt").write_text(f"ಕನ್ನಡ {i}\n", encoding="utf-8")
    files = pack(gt, tmp_path / "packs", size=2)
    assert [f.name for f in files] == ["pack-0000.lstmf", "pack-0001.lstmf"]
    assert all(f.stat().st_size > 0 for f in files)
    assert sorted(p.name for p in (tmp_path / "packs").iterdir()) == [
        "pack-0000.lstmf",
        "pack-0001.lstmf",
    ]
    assert sorted(p.name for p in gt.iterdir()) == [f"a_{i}.gt.txt" for i in range(3)]
    stamp = files[0].stat().st_mtime_ns
    assert pack(gt, tmp_path / "packs", size=2) == files
    assert files[0].stat().st_mtime_ns == stamp


def test_pack_refuses_an_empty_ground_truth_folder(tmp_path):
    from kannada_ocr.tesstrain import pack

    with pytest.raises(FileNotFoundError):
        pack(tmp_path, tmp_path / "packs")


ZWNJ = "\N{ZERO WIDTH NON-JOINER}"


def test_a_word_final_virama_gets_the_joiner_tesseract_expects():
    from kannada_ocr.tesstrain import tesseract_label

    assert tesseract_label("ಸರ್, ಎಸ್") == f"ಸರ್{ZWNJ}, ಎಸ್{ZWNJ}"
    assert tesseract_label("ಸ್ಮಿತ್ಎಂಬ") == f"ಸ್ಮಿತ್{ZWNJ}ಎಂಬ"
    assert tesseract_label(f"ಸ್ವಿಚ್{ZWNJ}ಗಳ ನ್ಯಾಷನಲ್{ZWNJ}") == f"ಸ್ವಿಚ್ಗಳ ನ್ಯಾಷನಲ್{ZWNJ}"


def test_export_applies_the_tesseract_label_rules(tmp_path):
    root = tmp_path / "set"
    (root / "images").mkdir(parents=True)
    Image.new("L", (20, 10), 0).save(root / "images" / "v.png")
    rows = [
        {"file_name": "images/v.png", "id": "v", "text": "ಸರ್, ಹೇಳಿ"},
        {"file_name": "images/v.png", "id": "e", "text": " "},
    ]
    (root / "metadata.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert export([Source("a", root)], tmp_path / "gt") == {"a": 1}
    assert (tmp_path / "gt" / "a_v.gt.txt").read_text(encoding="utf-8") == f"ಸರ್{ZWNJ}, ಹೇಳಿ\n"
