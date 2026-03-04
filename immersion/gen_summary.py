#!/usr/bin/env python3
"""Generate src/SUMMARY.md for the immersion guide mdbook."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STAGE_TITLES = {
    "stage1": "Stage 1 — First Contact (N5)",
    "stage2": "Stage 2 — Building the Habit (N4)",
    "stage3": "Stage 3 — Into Native Materials (N3)",
    "stage4": "Stage 4 — Native Content as Default (N2)",
    "stage5": "Stage 5 — Genre Mastery (N1)",
    "stage6": "Stage 6 — Unrestricted Immersion",
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
    """Return ordered list: stage_intro, chapters (sorted)."""
    files = []
    intro = stage_dir / "stage_intro.md"
    if intro.exists():
        files.append(intro)

    chapters = sorted(stage_dir.glob("ch*.md"))
    files.extend(chapters)

    return files


def create_symlinks():
    """Create symlinks in src/ pointing to actual content files."""
    src = ROOT / "src"
    src.mkdir(parents=True, exist_ok=True)

    # Symlink front_matter.md
    link = src / "front_matter.md"
    if not link.exists():
        link.symlink_to("../front_matter.md")

    # Symlink front_matter_stack.md
    link = src / "front_matter_stack.md"
    if not link.exists():
        link.symlink_to("../front_matter_stack.md")

    # Symlink each stage directory
    for stage_name in STAGE_TITLES:
        stage_dir = ROOT / stage_name
        if stage_dir.is_dir():
            link = src / stage_name
            if not link.exists():
                link.symlink_to(f"../{stage_name}")


def main():
    create_symlinks()

    lines = ["# Summary\n"]

    # Introduction (front matter)
    lines.append("[Introduction](front_matter.md)")
    lines.append("[The 2026 Learning Stack](front_matter_stack.md)\n")

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

    lines.append("")  # trailing newline

    out = ROOT / "src" / "SUMMARY.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {out}")


if __name__ == "__main__":
    main()
