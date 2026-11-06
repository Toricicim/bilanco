#!/usr/bin/env python3
"""Run the repository CLI from a Codex skill, without an extra model session."""

import os
import shutil
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[4]
    if not (root / "src/bilanco/cli.py").is_file():
        print(
            "Bilanco repo bulunamadı. Skill'i repo içinde veya ona symlink ile kullanın.",
            file=sys.stderr,
        )
        return 2
    uv = shutil.which("uv")
    executable = root / ".venv/bin/bilanco"
    if uv:
        args = [uv, "run", "--locked", "bilanco", *sys.argv[1:]]
    elif executable.is_file():
        args = [str(executable), *sys.argv[1:]]
    else:
        print("Önce Bilanco reposunda uv sync --locked çalıştırın.", file=sys.stderr)
        return 2
    os.chdir(root)
    os.execv(args[0], args)


if __name__ == "__main__":
    raise SystemExit(main())
