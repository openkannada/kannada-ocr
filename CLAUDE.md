# Claude Code

@AGENTS.md

AGENTS.md, imported above, is the canonical guide for this repository.

Claude-specific notes:

- Downloads, fonts and generated data go under `data/`, which is ignored. Commit only code, small results and docs.
- Before reporting a baseline number, rerun `uv run kocr eval` so the summary in `results/` matches the predictions file.
