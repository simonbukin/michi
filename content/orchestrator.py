"""Top-level batch runner + CLI for the content generation pipeline."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure content/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import OUTPUTS_DIR, CONFIG_DIR, VOCAB_LEDGER_PATH
from ledger.ledger import VocabLedger

SERIES_TITLE = "道"


def get_client():
    """Initialize Claude Code client (uses `claude -p` subprocess)."""
    from generator.claude_backend import ClaudeCodeClient
    return ClaudeCodeClient()


def write_output(data: bytes, stage: int, arc: str,
                  episode_id: str, ext: str) -> Path:
    """Write output file to the appropriate directory."""
    if ext in ("epub",):
        out_dir = OUTPUTS_DIR / f"stage{stage}" / "readers" / f"arc_{arc}"
    else:
        out_dir = OUTPUTS_DIR / f"stage{stage}" / "audio" / f"arc_{arc}"

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{episode_id}.{ext}"
    path.write_bytes(data)
    print(f"  Written: {path}")
    return path


def write_meta(meta: dict, stage: int, arc: str, episode_id: str) -> Path:
    """Write episode metadata JSON."""
    out_dir = OUTPUTS_DIR / f"stage{stage}" / "audio" / f"arc_{arc}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{episode_id}_meta.json"
    path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def cmd_generate(args):
    """Generate episodes."""
    from tqdm import tqdm
    from generator.generate_episode import (
        generate_reader_episode, generate_audio_episode,
        GenerationFailure, load_stage_config, load_characters,
    )
    from exporters.epub_exporter import build_epub
    from tts.audio_builder import build_episode_audio
    from exporters.transcript_exporter import build_transcript_html

    client = get_client()
    ledger = VocabLedger()
    ledger.load()

    stage = args.stage
    arc = args.arc
    n = args.n
    content_type = args.type

    types_to_generate = []
    if content_type in ("reader", "both"):
        types_to_generate.append("reader")
    if content_type in ("audio", "both"):
        types_to_generate.append("audio")

    chapter = getattr(args, 'chapter', None)

    for ctype in types_to_generate:
        ch_str = f", Ch.{chapter}" if chapter else ""
        print(f"\nGenerating {n} {ctype} episode(s) for Stage {stage}{ch_str}, {arc} arc...")

        for i in tqdm(range(n), desc=f"{ctype} episodes"):
            try:
                if ctype == "reader":
                    ep = generate_reader_episode(client, stage, arc, ledger,
                                                  chapter=chapter)
                    epub_bytes = build_epub([ep], stage, SERIES_TITLE)
                    write_output(epub_bytes, stage, arc, ep.id, "epub")
                    write_meta(ep.meta, stage, arc, ep.id)

                elif ctype == "audio":
                    ep = generate_audio_episode(client, stage, arc, ledger,
                                                 chapter=chapter)
                    stage_config = load_stage_config(stage)
                    characters = load_characters(stage)
                    audio_pkg = build_episode_audio(
                        ep.script, stage_config, characters)
                    html = build_transcript_html(
                        audio_pkg, ep.annotated_script, ep.id,
                        ep.outline.get("title", ep.id))
                    write_output(audio_pkg.mp3, stage, arc, ep.id, "mp3")
                    write_output(html.encode("utf-8"), stage, arc,
                                 f"{ep.id}_transcript", "html")
                    write_meta(ep.meta, stage, arc, ep.id)

            except GenerationFailure as e:
                print(f"\n  FAILED: {e}")
                continue
            except Exception as e:
                print(f"\n  ERROR: {e}")
                continue

    ledger.save()
    print("\nDone. Ledger saved.")


def cmd_status(args):
    """Show ledger status."""
    ledger = VocabLedger()
    ledger.load()

    if not VOCAB_LEDGER_PATH.exists():
        print("No ledger found. Run build first: cd shared/vocab && python3.11 build_master_vocab.py")
        return

    m = ledger.meta
    print(f"Current stage: {m['current_stage']}")
    print(f"Total episodes generated: {m['total_episodes_generated']}")
    print(f"Total characters generated: {m['total_characters_generated']}")
    print(f"Last updated: {m['last_updated']}")
    print()
    print(f"Words tracked: {len(ledger.words)}")
    print(f"  Active (count >= 10): {len(ledger.get_active_words())}")
    print(f"  Zone (count 3-9):     {len(ledger.get_zone_words())}")
    print(f"  New (count 1-2):      {len(ledger.get_new_words())}")
    print()
    print(f"Blacklisted situations: {len(ledger.episode_blacklist)}")

    # Show master vocab stats
    from paths import MASTER_VOCAB_PATH
    if MASTER_VOCAB_PATH.exists():
        master = json.loads(MASTER_VOCAB_PATH.read_text(encoding="utf-8"))
        stage_counts: dict[int, int] = {}
        for entry in master:
            s = entry["stage"]
            stage_counts[s] = stage_counts.get(s, 0) + 1
        print(f"\nMaster vocabulary ({len(master):,} entries):")
        for stage in range(1, 7):
            print(f"  Stage {stage}: {stage_counts.get(stage, 0)} entries")
    else:
        print("\nMaster vocab not found. Run: cd shared/vocab && python3.11 build_master_vocab.py")


def cmd_validate(args):
    """Validate an existing file."""
    from rule_engine.validator import validate

    ledger = VocabLedger()
    ledger.load()

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        return

    text = path.read_text(encoding="utf-8")
    stage = args.stage or 1
    content_type = "dialogue" if path.suffix == ".mp3" else "prose"

    result = validate(text, stage, content_type, ledger)
    print(f"Validation result: {'PASS' if result.passed else 'FAIL'}")
    print(f"  Hard fail: {result.hard_fail}")
    print(f"  Soft fail: {result.soft_fail}")
    print(f"  Vocab violation rate: {result.vocab.violation_rate:.4f}")
    print(f"  Comprehension estimate: {result.vocab.comprehension_estimate:.4f}")
    print(f"  Vocab violations: {len(result.vocab.violations)}")
    print(f"  Grammar violations: {len(result.grammar.violations)}")
    print(f"  Complexity violations: {len(result.complexity.violations)}")

    if result.vocab.violations:
        print("\n  Vocabulary violations:")
        for v in result.vocab.violations[:10]:
            print(f"    {v.surface} ({v.lemma})")

    if result.grammar.violations:
        print("\n  Grammar violations:")
        for v in result.grammar.violations[:10]:
            print(f"    {v.name} (stage {v.stage})")

    if result.complexity.violations:
        print("\n  Complexity violations:")
        for v in result.complexity.violations[:10]:
            print(f"    {v.issue}: {v.value} (threshold: {v.threshold})")


def main():
    parser = argparse.ArgumentParser(
        description="Michi Parallel Content System — Generate graded readers and audio dialogues")

    subparsers = parser.add_subparsers(dest="command")

    # Generate command (also default when using --stage etc.)
    gen_parser = subparsers.add_parser("generate", help="Generate episodes")
    gen_parser.add_argument("--stage", type=int, required=True, choices=range(1, 7))
    gen_parser.add_argument("--arc", type=str, required=True,
                            choices=["daily_life", "school", "seasonal", "social"])
    gen_parser.add_argument("--type", type=str, default="both",
                            choices=["reader", "audio", "both"])
    gen_parser.add_argument("--n", type=int, default=1, help="Number of episodes")
    gen_parser.add_argument("--chapter", type=int, default=None,
                            help="Chapter number for grammar gating (optional)")
    gen_parser.set_defaults(func=cmd_generate)

    # Status command
    status_parser = subparsers.add_parser("status", help="Show ledger status")
    status_parser.set_defaults(func=cmd_status)

    # Validate command
    val_parser = subparsers.add_parser("validate", help="Validate a file")
    val_parser.add_argument("file", help="Path to file to validate")
    val_parser.add_argument("--stage", type=int, default=1)
    val_parser.set_defaults(func=cmd_validate)

    # Support flat args for backwards compatibility with plan's CLI examples
    parser.add_argument("--stage", type=int, choices=range(1, 7))
    parser.add_argument("--arc", type=str,
                        choices=["daily_life", "school", "seasonal", "social"])
    parser.add_argument("--type", type=str, default="both",
                        choices=["reader", "audio", "both"])
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--chapter", type=int, default=None)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--validate", type=str, metavar="FILE")

    args = parser.parse_args()

    # Handle flat args
    if args.status:
        cmd_status(args)
    elif args.validate:
        args.file = args.validate
        cmd_validate(args)
    elif args.stage and args.arc:
        cmd_generate(args)
    elif hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
