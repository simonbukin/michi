#!/usr/bin/env python3
"""Generate src/SUMMARY.md for the colloquial patterns mdbook."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Ordered manifest: (directory, filename, part_title or None)
# Part titles use mdbook's `# Part Title` syntax for visual separators.
MANIFEST = [
    # Front matter (no part heading)
    (None, "front-matter.md", None),

    # Part I
    ("part-1-sentence-layer", "section-01-plain-form.md", "Part I — The Sentence Layer"),
    ("part-1-sentence-layer", "section-02-topic-drop.md", None),

    # Part II
    ("part-2-pragmatic-layer", "section-03-nda-family.md", "Part II — The Pragmatic Layer"),
    ("part-2-pragmatic-layer", "section-04-sentence-final-particles.md", None),

    # Part III
    ("part-3-phonological-compression", "section-05-verb-contractions.md", "Part III — Phonological Compression"),

    # Part IV
    ("part-4-claim-shaping", "section-06-hedges-softeners.md", "Part IV — Claim Shaping and Stance"),

    # Part V
    ("part-5-discourse-structure", "section-07-trailing-forms.md", "Part V — Discourse Structure"),
    ("part-5-discourse-structure", "section-08-connectives.md", None),

    # Appendix
    ("appendix", "appendix-written-casual.md", "Appendix"),

    # Back matter
    ("back-matter", "index-a-colloquial.md", "Back Matter"),
    ("back-matter", "index-b-formal.md", None),
    ("back-matter", "index-c-functional.md", None),
]


def get_heading(filepath: Path) -> str:
    """Read the first # heading from a markdown file."""
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    return filepath.stem


def create_symlinks():
    """Create symlinks in src/ pointing to actual content files."""
    src = ROOT / "src"
    src.mkdir(parents=True, exist_ok=True)

    # Track which directories we've already symlinked
    linked_dirs = set()

    for dir_name, filename, _ in MANIFEST:
        if dir_name is None:
            # Top-level file
            source = ROOT / filename
            link = src / filename
            if not link.exists() and source.exists():
                link.symlink_to(f"../{filename}")
        else:
            # Directory-based file — symlink the directory once
            if dir_name not in linked_dirs:
                link = src / dir_name
                if not link.exists() and (ROOT / dir_name).is_dir():
                    link.symlink_to(f"../{dir_name}")
                linked_dirs.add(dir_name)


def main():
    create_symlinks()

    lines = ["# Summary\n"]

    for dir_name, filename, part_title in MANIFEST:
        # Emit part heading if present
        if part_title:
            lines.append(f"\n# {part_title}\n")

        if dir_name is None:
            filepath = ROOT / filename
        else:
            filepath = ROOT / dir_name / filename

        if not filepath.exists():
            # Skip missing files silently during development
            continue

        heading = get_heading(filepath)
        if dir_name:
            rel = f"{dir_name}/{filename}"
        else:
            rel = filename
        lines.append(f"- [{heading}]({rel})")

    lines.append("")  # trailing newline

    out = ROOT / "src" / "SUMMARY.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {out}")


if __name__ == "__main__":
    main()
