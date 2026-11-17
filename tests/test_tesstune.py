import json
from pathlib import Path

import pytest

from kannada_ocr import cli, tesstune, text
from kannada_ocr.tesstune import Round, Settings, best_round, should_stop, tune


def test_training_stops_after_patience_rounds_without_a_real_gain():
    assert not should_stop([0.10, 0.09], patience=2)
    assert not should_stop([0.10, 0.09, 0.085], patience=2)
    assert should_stop([0.10, 0.09, 0.0895, 0.0899], patience=2)
    assert not should_stop([0.10, 0.09, 0.0895, 0.0885], patience=2)


def test_the_best_round_is_the_lowest_dev_cer_and_the_earliest_on_a_tie():
    rounds = [Round(n, cer, {}) for n, cer in [(1, 0.1), (2, 0.08), (3, 0.08), (4, 0.09)]]
    assert best_round(rounds) == 1


def fake_lstmtraining(rates):
    def run(*args, log):
        flags = dict(zip(args[1::2], args[2::2], strict=False))
        if args[0] == "--stop_training":
            Path(flags["--model_output"]).write_text(Path(flags["--continue_from"]).read_text())
            return
        if "--learning_rate" in args:
            assert args[args.index("--learning_rate") + 2] == "--reset_learning_rate"
            args = tuple(a for a in args if a != "--reset_learning_rate")
        flags = dict(zip(args[::2], args[1::2], strict=False))
        rates.append(flags.get("--learning_rate"))
        Path(flags["--model_output"] + "_checkpoint").write_text(flags["--max_iterations"])
        Path(flags["--model_output"] + "_5.1_10_100.checkpoint").write_text("")

    return run


def test_tune_keeps_the_best_round_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(tesstune, "_lstmtraining", fake_lstmtraining([]))
    out = tmp_path / "out"
    out.mkdir()
    dev = iter([0.10, 0.08, 0.085, 0.081, 0.07])

    def score(tessdata):
        return {"a": next(dev)}

    settings = Settings(round_lines=100, max_rounds=3, patience=2)
    tune(out, "kan_x", tmp_path / "s.lstm", tmp_path / "b", settings, score, log=lambda _: None)
    final = tune(
        out,
        "kan_x",
        tmp_path / "s.lstm",
        tmp_path / "b",
        Settings(round_lines=100, max_rounds=6, patience=2),
        score,
        log=lambda _: None,
    )
    record = json.loads((out / "tune-lr0.0001" / "rounds.json").read_text())
    assert [r["lines"] for r in record] == [100, 200, 300, 400]
    assert final.read_text() == "200"
    assert not list((out / "tune-lr0.0001").glob("kan_x_[0-9]*.checkpoint"))


def test_a_failed_lstmtraining_names_its_log(tmp_path, monkeypatch):
    class Failed:
        returncode = 1

    monkeypatch.setattr(tesstune.subprocess, "run", lambda *a, **k: Failed())
    log = tmp_path / "lstmtraining.log"
    log.write_text("round 1\nFinished! Selected model\n")
    with pytest.raises(RuntimeError, match="lstmtraining.log"):
        tesstune._lstmtraining("--stop_training", log=log)


def test_a_failure_after_training_finished_is_not_an_error(tmp_path, monkeypatch):
    class Failed:
        returncode = 1

    def run(command, stdout, stderr):
        stdout.write("At iteration 100\nFinished! Selected model\nAssert failed\n")
        return Failed()

    monkeypatch.setattr(tesstune.subprocess, "run", run)
    log = tmp_path / "lstmtraining.log"
    tesstune._lstmtraining("--max_iterations", "100", log=log)


def test_tune_can_keep_the_start_models_stored_rate(tmp_path, monkeypatch):
    rates = []
    monkeypatch.setattr(tesstune, "_lstmtraining", fake_lstmtraining(rates))
    out = tmp_path / "out"
    out.mkdir()
    settings = Settings(learning_rate=None, round_lines=100, max_rounds=1)
    tune(out, "kan_x", tmp_path / "s.lstm", tmp_path / "b", settings, lambda _: {"a": 0.1}, print)
    assert rates == [None]
    assert (out / "tune-stored" / "rounds.json").exists()


def test_tesstune_needs_the_scorer_before_it_trains(tmp_path, monkeypatch):
    def train(*args, log):
        raise AssertionError("trained without a scorer")

    monkeypatch.setattr(tesstune, "_lstmtraining", train)
    monkeypatch.setenv("KOCR_TEXT", str(tmp_path / "missing"))
    text.binary.cache_clear()
    try:
        with pytest.raises(FileNotFoundError, match="missing"):
            cli.main(["tesstune", "--model", "kan_x", "--out", str(tmp_path)])
    finally:
        text.binary.cache_clear()
