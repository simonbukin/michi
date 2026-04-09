#!/usr/bin/env python3
"""Generate src/SUMMARY.md for the Reading Companions mdbook."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Map directory names to display titles
SERIES_TITLES = {
    "onepiece": "One Piece",
}

VOLUME_TITLES = {
    "v01": "Volume 1",
    "v02": "Volume 2",
    "v03": "Volume 3",
}


def get_heading(filepath: Path) -> str:
    """Read the first # heading from a markdown file."""
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    return filepath.stem


def collect_volume_files(volume_dir: Path) -> list[Path]:
    """Return ordered list: ch00_*, ch01_*...ch99_*, appendix_*."""
    files = []
    chapters = sorted(volume_dir.glob("ch*.md"))
    files.extend(chapters)
    appendices = sorted(volume_dir.glob("appendix_*.md"))
    files.extend(appendices)
    return files


def create_symlinks():
    """Create symlinks in src/ pointing to actual content files."""
    src = ROOT / "src"
    src.mkdir(parents=True, exist_ok=True)

    # Symlink intro.md
    link = src / "intro.md"
    if not link.exists():
        link.symlink_to("../intro.md")

    # Symlink each series directory
    for series_dir in sorted(ROOT.iterdir()):
        if series_dir.is_dir() and series_dir.name not in ("src", "__pycache__"):
            link = src / series_dir.name
            if not link.exists():
                link.symlink_to(f"../{series_dir.name}")


def main():
    create_symlinks()

    lines = ["# Summary\n"]

    # Introduction
    lines.append("[Reading Companions](intro.md)\n")

    # Discover series directories
    series_dirs = sorted(
        d for d in ROOT.iterdir()
        if d.is_dir() and d.name not in ("src", "__pycache__")
    )

    for series_dir in series_dirs:
        series_title = SERIES_TITLES.get(series_dir.name, series_dir.name)
        lines.append(f"\n# {series_title}\n")

        # Discover volume directories within this series
        volume_dirs = sorted(
            d for d in series_dir.iterdir()
            if d.is_dir()
        )

        for volume_dir in volume_dirs:
            volume_title = VOLUME_TITLES.get(volume_dir.name, volume_dir.name)

            vol_files = collect_volume_files(volume_dir)
            if not vol_files:
                continue

            # First file becomes the section heading
            first = vol_files[0]
            heading = get_heading(first)
            rel = f"{series_dir.name}/{volume_dir.name}/{first.name}"
            lines.append(f"- [{volume_title}]({rel})")

            # Remaining files are nested
            for filepath in vol_files[1:]:
                heading = get_heading(filepath)
                rel = f"{series_dir.name}/{volume_dir.name}/{filepath.name}"
                lines.append(f"  - [{heading}]({rel})")

    lines.append("")  # trailing newline

    out = ROOT / "src" / "SUMMARY.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {out}")


if __name__ == "__main__":
    main()
