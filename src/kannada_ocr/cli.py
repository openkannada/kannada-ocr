"""Command line: `uv run kocr <command>`. Run `uv run kocr -h` for the list."""

from __future__ import annotations

import argparse
from pathlib import Path

from .http import Client

BENCH_SETS = ("mile-lines", "mile-pages", "degraded-words", "wikisource-old")


def _client(data: Path) -> Client:
    return Client(cache_dir=data / "cache" / "http", log_path=data / "sources" / "requests.jsonl")


def cmd_bench(args: argparse.Namespace) -> None:
    from . import bench

    data: Path = args.data
    mile_pages = data / "raw" / "mile" / "Kannada-OCR-test-images-with-ground-truth"
    mile_words = data / "raw" / "mile" / "DegradedWordsKannada"
    for name in args.sets:
        out = data / "bench" / name
        if name == "mile-lines":
            bench.build_mile_lines(mile_pages, out)
        elif name == "mile-pages":
            bench.build_mile_pages(mile_pages, out)
        elif name == "degraded-words":
            bench.build_degraded_words(mile_words, out)
        elif name == "wikisource-old":
            bench.build_wikisource_old(_client(data), out, pages_per_book=args.pages_per_book)


def cmd_wslines(args: argparse.Namespace) -> None:
    from . import wslines

    data: Path = args.data
    bench = data / "bench" / "wikisource-old"
    if args.fetch_only:
        print(f"{wslines.fetch(_client(data), bench, args.pages_per_book)} pages fetched")
        return
    wslines.build(
        _client(data),
        data / "train" / args.name,
        bench,
        data / "tessdata",
        [data / "bench" / name for name in BENCH_SETS],
        workers=args.workers,
        pages_per_book=args.pages_per_book,
    )


def cmd_tesstrain_gt(args: argparse.Namespace) -> None:
    from .fonts import KAGAPA, OFL
    from .tesstrain import Source, export, fetch_langdata

    data: Path = args.data
    lines = data / "train" / args.lines
    out = args.out or data / "train" / "tesstrain" / "data"
    synth = data / "synth" / "synth-v0"
    train = [
        Source("ws", lines, split="train"),
        *(
            Source(
                "ofl" if name == "synth-v0" else f"ofl-{name}",
                data / "synth" / name,
                count=args.ofl,
                font_license=OFL,
            )
            for name in args.synth
        ),
        Source("nudiuni", synth, count=args.kagapa, font_license=KAGAPA),
        Source("nudi", data / "synth" / "synth-v0-nudi", count=args.kagapa),
    ]
    dev = [
        Source("wsdev", lines, split="dev"),
        Source("miledev", data / "bench" / "mile-lines", split="dev", count=args.mile_dev),
    ]
    fetch_langdata(_client(data), out / "langdata")
    print("train", export([s for s in train if s.count != 0], out / f"{args.model}-ground-truth"))
    print("dev", export(dev, out / f"{args.model}-dev-ground-truth"))


def cmd_tesstrain_pack(args: argparse.Namespace) -> None:
    from .tesstrain import pack

    out = args.out or args.data / "train" / "tesstrain" / "data"
    model = out / args.model
    model.mkdir(parents=True, exist_ok=True)
    for gt, packs, listfile in (
        (f"{args.model}-ground-truth", model / "packs", model / "list.train"),
        (
            f"{args.model}-dev-ground-truth",
            out / f"{args.model}-dev" / "packs",
            model / "list.eval",
        ),
    ):
        files = pack(out / gt, packs, workers=args.workers)
        listfile.write_text("".join(f"{f}\n" for f in files))
        print(f"{listfile.name}: {len(files)} files")


def cmd_tesstune(args: argparse.Namespace) -> None:
    import shutil

    from . import text
    from .tesstune import Settings, dev_score, tune, tune_dir

    text.binary()  # dev scoring needs it; check before the first round of training
    data: Path = args.data
    out = (args.out or data / "train" / "tesstrain" / "data") / args.model
    settings = Settings(args.learning_rate, args.round_lines, args.max_rounds, args.patience)
    results = tune_dir(out, settings) / "dev-results"
    model = tune(
        out,
        args.model,
        out.parent / "kan" / f"{args.model}.lstm",
        data / "tessdata" / "kan.traineddata",
        settings,
        lambda tessdata: dev_score(tessdata, args.model, data / "bench", results),
    )
    name = args.name or args.model
    shutil.copy(model, data / "tessdata" / f"{name}.traineddata")
    print(f"wrote {data / 'tessdata' / name}.traineddata")


def _recognizer(name: str, data: Path):
    if name.startswith("tesseract"):
        from .baselines.tesseract import Tesseract

        name, _, lang = name.partition("@")
        mode = name.removeprefix("tesseract").removeprefix("-psm")
        return Tesseract(data / "tessdata", lang=lang or "kan", page_mode=int(mode) if mode else 3)
    from .baselines.vlm import VLM

    return VLM(name)


def cmd_eval(args: argparse.Namespace) -> None:
    from .evaluate import evaluate
    from .text import telugu_as_kannada

    recognizer = _recognizer(args.model, args.data)
    split = None if args.split == "all" else args.split
    transform = telugu_as_kannada if args.telugu_as_kannada else None
    for name in args.sets:
        bench = args.data / "bench" / name
        evaluate(recognizer, bench, args.results, split, args.limit, transform=transform)


def cmd_fonts(args: argparse.Namespace) -> None:
    from . import fonts

    fonts.download(_client(args.data), args.data / "fonts", kagapa=args.kagapa)
    for font in fonts.inventory(args.data / "fonts"):
        digits = f"  (digits: {font.digit_style})" if font.digit_style else ""
        print(f"{font.design:24} {font.face.name}{digits}")


def cmd_corpus(args: argparse.Namespace) -> None:
    from . import corpus

    raw = args.data / "raw" / "text"
    corpus.build_lines(
        {
            "wikipedia": raw / "wikipedia-20231101.kn.parquet",
            "wikisource": raw / "wikisource-20231201.kn.parquet",
        },
        [args.data / "bench" / name for name in BENCH_SETS],
        args.data / "corpus" / "lines.tsv",
        per_source=args.per_source,
    )


def cmd_synth(args: argparse.Namespace) -> None:
    from . import corpus, fonts, synth, text

    if args.fonts != "ofl" and not (args.data / "fonts" / "nudi").is_dir():
        raise SystemExit(f"--fonts {args.fonts} needs the Nudi fonts; run `kocr fonts --kagapa`")
    lines = corpus.read_lines(args.data / "corpus" / "lines.tsv")
    chosen = []
    if args.fonts in ("unicode", "all"):
        chosen += fonts.inventory(args.data / "fonts")
    if args.fonts == "ofl":
        chosen += [f for f in fonts.inventory(args.data / "fonts") if f.license == fonts.OFL]
    if args.fonts in ("legacy", "all"):
        chosen += fonts.legacy_inventory(args.data / "fonts")
    nudi = text.to_nudi([line for _, line in lines]) if args.fonts in ("legacy", "all") else []
    plan = synth.Plan(
        lines=lines,
        fonts=chosen,
        seed=args.seed,
        nudi=tuple(nudi),
        profile_weights=tuple(args.profile_weights or synth.PROFILE_WEIGHTS),
    )
    out = args.data / "synth" / args.name
    summary = synth.generate(plan, out, args.count, workers=args.workers)
    synth.preview(out, out / "preview.png")
    print({k: summary[k] for k in ("samples", "skipped_missing_glyphs", "bytes", "stopped_early")})


def cmd_report(args: argparse.Namespace) -> None:
    from .report import by_book, table

    if args.by_book:
        print(by_book(args.results, args.by_book, args.split), end="")
    else:
        print(table(args.results, args.split), end="")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kocr", description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"), help="data directory")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("bench", help="build evaluation sets")
    p.add_argument("sets", nargs="*", choices=BENCH_SETS, default=list(BENCH_SETS))
    p.add_argument("--pages-per-book", type=int, default=8)
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("fonts", help="download fonts and list the usable ones")
    p.add_argument(
        "--kagapa",
        action="store_true",
        help="also download KaGaPa's Nudi fonts, which have no license; keep their images local",
    )
    p.set_defaults(func=cmd_fonts)

    p = sub.add_parser("corpus", help="cut text lines for rendering from the text dumps")
    p.add_argument("--per-source", type=int, default=200_000)
    p.set_defaults(func=cmd_corpus)

    p = sub.add_parser("synth", help="render and degrade synthetic line images")
    p.add_argument("--name", default="synth-v0")
    p.add_argument("--count", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument(
        "--fonts",
        choices=("unicode", "ofl", "legacy", "all"),
        default="ofl",
        help="ofl: only OFL fonts, shareable; unicode adds KaGaPa's Unicode Nudi fonts, and "
        "legacy its legacy Nudi fonts through kannadi's encoder; keep Nudi images local",
    )
    p.add_argument(
        "--profile-weights",
        type=float,
        nargs=3,
        metavar=("CLEAN", "PRINT", "LETTERPRESS"),
        help="shares of the 3 damage profiles; 0.2 0.4 0.4 by default",
    )
    p.set_defaults(func=cmd_synth)

    p = sub.add_parser("wslines", help="cut labeled training lines from Wikisource scans")
    p.add_argument("--fetch-only", action="store_true", help="download pages and scans, no OCR")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--pages-per-book", type=int, default=40, help="for books outside the benchmark")
    p.add_argument("--name", default="wikisource-lines", help="output folder under data/train")
    p.set_defaults(func=cmd_wslines)

    p = sub.add_parser("tesstrain-gt", help="write tesstrain ground truth for fine-tuning")
    p.add_argument("--model", default="kan_ft_ofl2")
    p.add_argument("--ofl", type=int, help="OFL-font lines per synthetic set; all by default")
    p.add_argument(
        "--kagapa",
        type=int,
        default=0,
        help="lines in KaGaPa Nudi fonts from each of synth-v0 and synth-v0-nudi; such a model "
        "stays local",
    )
    p.add_argument("--mile-dev", type=int, default=300, help="MILE dev lines for checkpoints")
    p.add_argument(
        "--lines", default="wikisource-lines-120", help="Wikisource line folder in data/train"
    )
    p.add_argument(
        "--synth",
        nargs="+",
        default=["synth-v0", "synth-v1-ofl"],
        help="synthetic sets to take OFL lines from",
    )
    p.add_argument("--out", type=Path, help="tesstrain data directory")
    p.set_defaults(func=cmd_tesstrain_gt)

    p = sub.add_parser("tesstune", help="fine-tune in rounds and keep the best round on dev")
    p.add_argument("--model", default="kan_ft_ofl2")
    p.add_argument("--name", help="name of the result in data/tessdata; the model's by default")
    p.add_argument(
        "--learning-rate",
        type=lambda v: None if v == "stored" else float(v),
        default=None,
        help="a rate, or 'stored' for the rate stored in the start model",
    )
    p.add_argument("--round-lines", type=int, default=10_000)
    p.add_argument("--max-rounds", type=int, default=12)
    p.add_argument("--patience", type=int, default=2)
    p.add_argument("--out", type=Path, help="tesstrain data directory")
    p.set_defaults(func=cmd_tesstune)

    p = sub.add_parser("tesstrain-pack", help="build the .lstmf files and lists for lstmtraining")
    p.add_argument("--model", default="kan_ft_ofl2")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--out", type=Path, help="tesstrain data directory")
    p.set_defaults(func=cmd_tesstrain_pack)

    p = sub.add_parser("eval", help="run a baseline on evaluation sets")
    p.add_argument(
        "model",
        help="'tesseract', 'tesseract-psm4', 'tesseract@<lang>' for data/tessdata/<lang>"
        ".traineddata, or an mlx-vlm model id",
    )
    p.add_argument("sets", nargs="+", choices=BENCH_SETS)
    p.add_argument("--split", default="test", choices=("test", "dev", "all"))
    p.add_argument("--limit", type=int, help="score a fixed sample of this many items")
    p.add_argument("--results", type=Path, default=Path("results"))
    p.add_argument(
        "--telugu-as-kannada",
        action="store_true",
        help="diagnostic: score predictions with Telugu letters moved to Kannada",
    )
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("report", help="print a markdown table of the results for 1 split")
    p.add_argument("--results", type=Path, default=Path("results"))
    p.add_argument("--split", default="test", help="dev, test or all")
    p.add_argument("--by-book", metavar="SET", help="CER per book on 1 set instead")
    p.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
