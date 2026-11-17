# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

from PIL import Image

from kannada_ocr.baselines.vlm import MIN_HEIGHT, enlarged, strip_markup


def test_markup_and_end_tokens_are_removed():
    assert strip_markup("```text\nಕನ್ನಡ\n```<|im_end|>") == "ಕನ್ನಡ"
    assert strip_markup("  ಕನ್ನಡ<|endoftext|>") == "ಕನ್ನಡ"


def test_small_images_are_enlarged_and_large_ones_kept(tmp_path):
    small, large = tmp_path / "s.png", tmp_path / "l.png"
    Image.new("L", (100, 40)).save(small)
    Image.new("L", (100, 200)).save(large)
    with Image.open(enlarged(small, tmp_path)) as im:
        assert im.size == (240, MIN_HEIGHT)
    assert enlarged(large, tmp_path) == large


def test_the_model_is_not_loaded_until_needed():
    from kannada_ocr.baselines.vlm import VLM

    model = VLM("mlx-community/some-model-4bit")
    assert model.name == "some-model-4bit" and model._loaded is None
