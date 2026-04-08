"""Sequential stage generation harness.

Generates all episodes for a stage in frequency order, accumulating
the ledger naturally. Supports chapter-level grammar gating.

Usage:
    python3.11 generate_stage.py --stage 2 --dry-run
    python3.11 generate_stage.py --stage 2 --chapters 1-3
    python3.11 generate_stage.py --stage 2 --episodes-per-chapter 5
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import CONFIG_DIR, OUTPUTS_DIR
from ledger.ledger import VocabLedger


# Stage chapter counts (from textbook TOCs)
STAGE_CHAPTERS = {
    1: 26,
    2: 29,
    3: 30,  # approximate
    4: 25,
    5: 20,
    6: 15,
}

# New words per stage
STAGE_NEW_WORDS = {1: 800, 2: 700, 3: 1500, 4: 2000, 5: 3000, 6: 2000}


def load_episode_counts() -> dict:
    """Load episode count config."""
    path = CONFIG_DIR / "episode_counts.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"default_episodes_per_chapter": 8, "overrides": {}}


def load_stage_config(stage: int) -> dict:
    """Load stage config from stages.json."""
    stages_path = CONFIG_DIR / "stages.json"
    stages = json.loads(stages_path.read_text(encoding="utf-8"))
    return stages[str(stage)]


def get_episodes_for_chapter(stage: int, chapter: int,
                              ep_config: dict) -> int:
    """Get number of episodes for a specific chapter."""
    key = f"{stage}.{chapter}"
    overrides = ep_config.get("overrides", {})
    return overrides.get(key, ep_config.get("default_episodes_per_chapter", 8))


def parse_chapters_arg(chapters_str: str, max_chapter: int) -> list[int]:
    """Parse '1-3' or '5' into list of chapter numbers."""
    if "-" in chapters_str:
        start, end = chapters_str.split("-", 1)
        return list(range(int(start), min(int(end), max_chapter) + 1))
    return [int(chapters_str)]


def dry_run(stage: int, chapters: list[int], ep_config: dict):
    """Show what would be generated without generating anything."""
    stage_config = load_stage_config(stage)
    new_per_ep = stage_config["new_words_per_episode"]
    chars_per_ep = stage_config["target_text_chars"]
    total_new = STAGE_NEW_WORDS[stage]

    print(f"\n{'=' * 60}")
    print(f"DRY RUN: Stage {stage}")
    print(f"{'=' * 60}")
    print(f"  New words per episode: {new_per_ep}")
    print(f"  Chars per episode: {chars_per_ep}")
    print(f"  Total new words: {total_new}")

    words_allocated = 0
    total_episodes = 0
    total_chars = 0

    # Load grammar schedule for display
    schedule_path = CONFIG_DIR / "grammar_schedule.json"
    schedule = {}
    if schedule_path.exists():
        schedule = json.loads(schedule_path.read_text(encoding="utf-8"))

    print(f"\n  {'Ch':>4} {'Eps':>4} {'NewW':>5} {'Chars':>7} {'Grammar introduced'}")
    print(f"  {'─' * 4} {'─' * 4} {'─' * 5} {'─' * 7} {'─' * 35}")

    for ch in chapters:
        n_eps = get_episodes_for_chapter(stage, ch, ep_config)
        words_this_ch = min(n_eps * new_per_ep, total_new - words_allocated)
        chars_this_ch = n_eps * chars_per_ep

        # Grammar introduced at this chapter
        grammar_here = [
            name for name, entry in schedule.items()
            if not name.startswith("_")
            and entry["stage"] == stage
            and entry["chapter"] == ch
        ]
        grammar_str = ", ".join(grammar_here) if grammar_here else "—"

        print(f"  {ch:>4} {n_eps:>4} {words_this_ch:>5} "
              f"{chars_this_ch:>7,} {grammar_str}")

        words_allocated += words_this_ch
        total_episodes += n_eps
        total_chars += chars_this_ch

    # Comprehension estimate
    ct = int(chars_per_ep * 0.25)
    comp = 1.0 - (new_per_ep * 1.3 / ct)

    print(f"\n  Total: {total_episodes} episodes, {total_chars:,} chars")
    print(f"  Words allocated: {words_allocated}/{total_new}")
    print(f"  Comprehension estimate: {comp:.1%}")

    if words_allocated < total_new:
        remaining = total_new - words_allocated
        extra_eps = remaining // new_per_ep
        print(f"\n  Note: {remaining} words remaining, need ~{extra_eps} more episodes")


def generate(stage: int, chapters: list[int], ep_config: dict,
             arc: str = "daily_life"):
    """Generate episodes for the specified chapters."""
    from tqdm import tqdm
    from generator.generate_episode import (
        generate_reader_episode, GenerationFailure,
    )
    from exporters.epub_exporter import build_epub
    from orchestrator import get_client, write_output, write_meta, SERIES_TITLE

    client = get_client()
    ledger = VocabLedger()
    ledger.load()

    stage_config = load_stage_config(stage)

    total_generated = 0
    total_failed = 0

    for ch in chapters:
        n_eps = get_episodes_for_chapter(stage, ch, ep_config)
        print(f"\n--- Chapter {ch}: {n_eps} episodes ---")

        for i in tqdm(range(n_eps), desc=f"S{stage}Ch{ch}"):
            try:
                ep = generate_reader_episode(
                    client, stage, arc, ledger, chapter=ch)

                epub_bytes = build_epub([ep], stage, SERIES_TITLE)
                write_output(epub_bytes, stage, arc, ep.id, "epub")
                write_meta(ep.meta, stage, arc, ep.id)

                total_generated += 1

            except GenerationFailure as e:
                print(f"\n  FAILED: {e}")
                total_failed += 1
                continue
            except Exception as e:
                print(f"\n  ERROR: {e}")
                total_failed += 1
                continue

        ledger.save()

    print(f"\nDone. Generated: {total_generated}, Failed: {total_failed}")
    print(f"Ledger saved.")


def main():
    parser = argparse.ArgumentParser(
        description="Sequential stage generation harness")
    parser.add_argument("--stage", type=int, required=True, choices=range(1, 7))
    parser.add_argument("--chapters", type=str, default=None,
                        help="Chapter range (e.g. '1-3' or '5'). Default: all")
    parser.add_argument("--episodes-per-chapter", type=int, default=None,
                        help="Override default episodes per chapter")
    parser.add_argument("--arc", type=str, default="daily_life",
                        choices=["daily_life", "school", "seasonal", "social"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without generating")

    args = parser.parse_args()

    ep_config = load_episode_counts()
    if args.episodes_per_chapter:
        ep_config["default_episodes_per_chapter"] = args.episodes_per_chapter

    max_ch = STAGE_CHAPTERS.get(args.stage, 30)

    if args.chapters:
        chapters = parse_chapters_arg(args.chapters, max_ch)
    else:
        chapters = list(range(1, max_ch + 1))

    if args.dry_run:
        dry_run(args.stage, chapters, ep_config)
    else:
        generate(args.stage, chapters, ep_config, arc=args.arc)


if __name__ == "__main__":
    main()
