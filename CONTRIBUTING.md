# Contributing to kannada-ocr

Thank you for helping. Wrong readings, bugs, sample pages and ideas go in [GitHub issues](https://github.com/openkannada/kannada-ocr/issues). Include the image or a link to it, the command you ran and what you expected. For a security problem, follow [SECURITY.md](SECURITY.md) instead.

## Sign off every commit (DCO)

Open Kannada uses the [Developer Certificate of Origin](https://developercertificate.org/) (DCO), not a contributor license agreement. Every commit needs a `Signed-off-by` line with your name and email. It certifies that you wrote the change, or otherwise have the right to submit it under this repository's licenses.

`git commit -s` adds the line from your Git settings:

```text
Signed-off-by: Your Name <you@example.com>
```

If you forgot, `git commit --amend -s` signs off the last commit, and `git rebase --signoff origin/main` signs off every commit on your branch.

You keep the copyright in your work. It is licensed under the licenses of the files it changes, as the README's License section describes, and you join "The Open Kannada Authors".

CI checks every commit in a pull request for the line.

## Making a change

[AGENTS.md](AGENTS.md) has the commands, the layout and the rules, for people and AI agents alike. Before you open a pull request, run:

```sh
cargo build --release && cargo test
cargo fmt --all && cargo clippy --all-targets -- -D warnings
uv run pytest
uv run ruff check . && uv run ruff format --check .
uvx reuse lint
```

Never commit MILE images, text or OCR output of MILE pages, images rendered with Nudi fonts, or any data whose license does not allow redistribution. A book whose license tag looks wrong goes in `sources/excluded-training-books.json` with the reason.
