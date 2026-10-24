# Repository instructions for coding agents

Read `CONTRIBUTING.md` and `README.md` before changing this repository. These rules apply to the entire repository and every coding agent working on it.

## Git workflow — mandatory

- Never commit directly on `main`, push directly to `main`, or force-push any shared branch. Do not bypass branch protections.
- Inspect `git status`, the current branch, and the relevant diff before edits or commits. Preserve existing user changes.
- Use a separate branch for each independent feature, fix, or documentation task. Start new independent work from current `origin/main`; continue the same task on its existing branch. Use `feat/`, `fix/`, `docs/`, or `refactor/` names.
- If work is already uncommitted on `main`, create a task branch preserving it before committing. Never discard user changes to obtain a clean checkout.
- Separate concurrent independent work into different worktrees/checkouts. Do not switch a shared working directory out from under another worker.
- Stage only relevant files. Review the staged diff and run appropriate checks before committing.
- When asked to publish work, push the task branch and open a PR targeting `main`. Report the PR link. Do not merge or enable auto-merge without an explicit instruction from the project owner.
- Update an existing task PR through normal commits and pushes. Do not fold unrelated tasks into it.

## Project invariants

- Keep Enron and Turkey paths functional; do not hard-code company-specific alarm outcomes.
- Respect the historical information cutoff. Do not use later events or known fraud outcomes as historical inputs. Preserve source identity, publication date, quoted evidence and counterevidence.
- Missing data is unknown, not proof of safety. Context, review candidates, deterministic findings, and calibrated probabilities are different; do not inflate one into another.
- Real financial acquisition/model analysis starts only through an explicitly requested run. Development tests use synthetic data and must not make real financial HTTP/model calls.
- Preserve existing run snapshots; create new run IDs for new results. The CLI stays headless; prepare HTML separately from saved JSON only when requested. Never invent values to fill a demo.
- Never commit secrets, `.env`, auth files, database dumps, or new raw/runtime analysis data. Existing tracked historical snapshots are not permission to publish new runtime data.
- Update relevant repository documentation for meaningful behavior changes. Never claim unexecuted checks passed or a partial run proved fraud-detection success.

## Checks

For code changes: `uv run ruff check .`, `uv run ruff format --check .`, and relevant `uv run pytest -q` tests. Broaden tests when shared behavior changes. PostgreSQL tests must use a separate database named `bilanco_test_*`, never the user's analysis database. Follow README for setup. For docs-only work, verify commands, paths, links and `git diff --check`; do not launch paid/live analysis merely to validate documentation.
