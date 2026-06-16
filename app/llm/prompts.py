from __future__ import annotations

from pathlib import Path


PROMPT_DIR = Path("prompts")


def load_prompt(name: str) -> str:
    path = PROMPT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")
