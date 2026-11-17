import numpy as np
import pytest

from kannada_ocr.degrade import MIN_INK_KEPT, PROFILES, degrade, stroke_weight, wear


def strokes(width: int = 3) -> np.ndarray:
    ink = np.zeros((40, 120), dtype=np.float32)
    for x in range(10, 110, 12):
        ink[8:32, x : x + width] = 1.0
    return ink


@pytest.mark.parametrize("profile", PROFILES)
def test_degrade_is_reproducible_and_in_range(profile):
    a, pa = degrade(strokes(), profile, np.random.default_rng(7), ghost=strokes())
    b, pb = degrade(strokes(), profile, np.random.default_rng(7), ghost=strokes())
    assert pa == pb and pa["profile"] == profile
    assert np.array_equal(a, b)
    assert a.min() >= 0.0 and a.max() <= 1.0


def test_text_stays_darker_than_paper():
    for seed in range(20):
        page, p = degrade(strokes(), "print", np.random.default_rng(seed))
        assert "skew" in p
        assert page.min() < page.mean() - 0.1


def test_stroke_weight_spreads_or_thins_ink():
    ink = strokes()
    assert stroke_weight(ink, 0.3, 1.0).sum() > ink.sum()
    assert stroke_weight(ink, 0.7, 1.0).sum() < ink.sum()


def test_wear_never_erases_thin_strokes():
    thin = strokes(width=1) * 0.6
    for seed in range(40):
        worn = wear(thin, np.random.default_rng(seed), {})
        assert worn.sum() >= MIN_INK_KEPT * thin.sum()


def test_unknown_profile_is_an_error():
    with pytest.raises(ValueError):
        degrade(strokes(), "fax", np.random.default_rng(0))
