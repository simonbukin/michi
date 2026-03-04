#!/usr/bin/env python3
"""Generate src/SUMMARY.md for mdbook from the existing stage directories."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STAGE_TITLES = {
    "stage1": "Stage 1 — Foundations (N5)",
    "stage2": "Stage 2 — Essential Grammar (N4)",
    "stage3": "Stage 3 — Bridging to the Real World (N3)",
    "stage4": "Stage 4 — Advanced Proficiency (N2)",
    "stage5": "Stage 5 — N2→N1 Bridge (N1)",
    "stage6": "Stage 6 — N1 Mastery",
}


def get_heading(filepath: Path) -> str:
    """Read the first # heading from a markdown file."""
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    return filepath.stem


def collect_stage_files(stage_dir: Path) -> list[Path]:
    """Return ordered list: stage_intro, chapters (sorted), appendices (sorted)."""
    files = []
    intro = stage_dir / "stage_intro.md"
    if intro.exists():
        files.append(intro)

    chapters = sorted(stage_dir.glob("ch*.md"))
    files.extend(chapters)

    appendices = sorted(stage_dir.glob("appendix_*.md"))
    files.extend(appendices)

    return files


def main():
    lines = ["# Summary\n"]

    # Introduction (front matter)
    lines.append("[Introduction](front_matter.md)\n")

    # Each stage as a Part
    for stage_name, stage_title in STAGE_TITLES.items():
        stage_dir = ROOT / stage_name
        if not stage_dir.is_dir():
            continue

        lines.append(f"\n# {stage_title}\n")

        for filepath in collect_stage_files(stage_dir):
            heading = get_heading(filepath)
            rel = f"{stage_name}/{filepath.name}"
            lines.append(f"- [{heading}]({rel})")

    # Reference section
    lines.append("\n# Reference\n")
    lines.append("- [Grammar Index](grammar_index.md)")
    lines.append("- [Vocabulary Index](vocabulary_index.md)")

    lines.append("")  # trailing newline

    out = ROOT / "src" / "SUMMARY.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {out}")


if __name__ == "__main__":
    main()
