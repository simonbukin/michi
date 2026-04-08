"""Orchestrates the outline → prose → validate loop for episode generation."""

import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import CONFIG_DIR
from generator.outline_gen import generate_outline
from generator.prose_gen import generate_prose
from generator.correction_gen import correct_text
from rule_engine.validator import validate, load_stage_config
from annotator.annotator import annotate


class GenerationFailure(Exception):
    pass


@dataclass
class ReaderEpisode:
    id: str
    outline: dict
    raw: str
    annotated: object  # AnnotatedText
    meta: dict
    curated_notes: object = None  # CuratedNotes, set after annotation


@dataclass
class DialogueTurn:
    character: str
    text: str


@dataclass
class AudioEpisode:
    id: str
    outline: dict
    raw: str
    script: list[DialogueTurn]
    annotated_script: list  # list of AnnotatedText per turn
    meta: dict


def load_characters(stage: int) -> dict:
    """Load characters available at the given stage."""
    chars_path = CONFIG_DIR / "characters.json"
    all_chars = json.loads(chars_path.read_text(encoding="utf-8"))
    return {
        name: data for name, data in all_chars.items()
        if data["stage_introduced"] <= stage
    }


def load_situation_pools() -> dict:
    """Load situation pools from config."""
    pools_path = CONFIG_DIR / "situation_pools.json"
    return json.loads(pools_path.read_text(encoding="utf-8"))


def pick_situation(arc: str, stage: int, blacklist: list[str]) -> str:
    """Pick a random situation from the arc pool, avoiding blacklisted ones."""
    pools = load_situation_pools()
    pool = pools.get(arc, [])
    available = [s for s in pool if s not in blacklist]
    if not available:
        available = pool  # Reset if all are blacklisted
    if not available:
        return "日常の一場面"  # Fallback
    return random.choice(available)


def parse_dialogue(text: str) -> list[DialogueTurn]:
    """Parse dialogue text in format: キャラ名:「セリフ」"""
    turns = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or "「" not in line:
            continue
        # Split on first : or ：
        for sep in [":", "："]:
            if sep in line:
                parts = line.split(sep, 1)
                character = parts[0].strip()
                dialogue = parts[1].strip().strip("「」")
                turns.append(DialogueTurn(character=character, text=dialogue))
                break
    return turns


_episode_counter = 0


def generate_episode_id(stage: int, arc: str, ledger) -> str:
    """Generate a unique episode ID. Uses a session counter to avoid collisions."""
    global _episode_counter
    _episode_counter += 1
    base = ledger.meta["total_episodes_generated"] + _episode_counter
    return f"s{stage}_{arc}_ep{base:03d}"


def generate_reader_episode(client, stage: int, arc: str,
                             ledger, max_attempts: int = 5,
                             chapter: int | None = None) -> ReaderEpisode:
    """Generate a complete reader episode with validation loop.

    Args:
        chapter: Optional chapter number for chapter-level grammar gating.
                 When None, defaults to stage-level ceiling (all grammar for the stage).
    """
    stage_config = load_stage_config(stage)
    characters = load_characters(stage)
    ledger_summary = ledger.get_prompt_summary(stage)
    situation = pick_situation(arc, stage, ledger.get_blacklist())
    episode_id = generate_episode_id(stage, arc, ledger)

    # Step 1: Generate outline
    outline = generate_outline(
        client, stage_config, ledger_summary, characters,
        situation, arc, content_type="reader")

    # Step 2: Generate prose (with vocab list constraint)
    raw_text = generate_prose(
        client, outline, stage_config, characters,
        ledger_summary, content_type="reader")

    # Step 3: Validate + correct loop
    for attempt in range(max_attempts):
        result = validate(raw_text, stage, "prose", ledger, chapter=chapter)
        if result.passed:
            break
        if result.hard_fail:
            raw_text = correct_text(
                client, raw_text, result.vocab.violations,
                "vocab", stage_config)
        elif result.soft_fail:
            raw_text = correct_text(
                client, raw_text, result.complexity.violations,
                "complexity", stage_config)
    else:
        raise GenerationFailure(
            f"Failed to generate valid episode after {max_attempts} attempts. "
            f"Last validation: vocab={result.vocab.violation_rate:.3f}, "
            f"grammar_violations={len(result.grammar.violations)}, "
            f"complexity_violations={len(result.complexity.violations)}")

    # Annotate
    furigana_threshold = stage_config.get("furigana_threshold", 8)
    annotated = annotate(raw_text, stage, ledger, furigana_threshold)

    # Update ledger
    lemmas = [t.lemma for t in annotated.tokens]
    delta = ledger.record_episode(lemmas, episode_id)
    ledger.add_to_blacklist(situation)
    ledger.save()

    meta = {
        "episode_id": episode_id,
        "stage": stage,
        "arc": arc,
        "situation": situation,
        "generated_at": datetime.now().isoformat(),
        "content_type": "reader",
        "validation": {
            "vocab_violation_rate": result.vocab.violation_rate,
            "grammar_violations": [t.id for t in result.grammar.violations],
            "comprehension_estimate": result.vocab.comprehension_estimate,
            "attempts_needed": attempt + 1,
        },
        "ledger_delta": delta,
    }

    return ReaderEpisode(
        id=episode_id, outline=outline, raw=raw_text,
        annotated=annotated, meta=meta)


def generate_audio_episode(client, stage: int, arc: str,
                            ledger, max_attempts: int = 5,
                            chapter: int | None = None) -> AudioEpisode:
    """Generate a complete audio episode with validation loop.

    Args:
        chapter: Optional chapter number for chapter-level grammar gating.
    """
    stage_config = load_stage_config(stage)
    characters = load_characters(stage)
    ledger_summary = ledger.get_prompt_summary(stage)
    situation = pick_situation(arc, stage, ledger.get_blacklist())
    episode_id = generate_episode_id(stage, arc, ledger)

    # Step 1: Generate outline
    outline = generate_outline(
        client, stage_config, ledger_summary, characters,
        situation, arc, content_type="audio")

    # Step 2: Generate dialogue
    raw_text = generate_prose(
        client, outline, stage_config, characters,
        ledger_summary, content_type="audio")

    # Step 3: Validate + correct loop
    for attempt in range(max_attempts):
        result = validate(raw_text, stage, "dialogue", ledger, chapter=chapter)
        if result.passed:
            break
        if result.hard_fail:
            raw_text = correct_text(
                client, raw_text, result.vocab.violations,
                "vocab", stage_config)
        elif result.soft_fail:
            raw_text = correct_text(
                client, raw_text, result.complexity.violations,
                "complexity", stage_config)
    else:
        raise GenerationFailure(
            f"Failed to generate valid dialogue after {max_attempts} attempts.")

    # Parse dialogue turns
    script = parse_dialogue(raw_text)

    # Annotate each turn
    furigana_threshold = stage_config.get("furigana_threshold", 8)
    annotated_script = []
    all_lemmas = []
    for turn in script:
        ann = annotate(turn.text, stage, ledger, furigana_threshold)
        annotated_script.append(ann)
        all_lemmas.extend(t.lemma for t in ann.tokens)

    # Update ledger
    delta = ledger.record_episode(all_lemmas, episode_id)
    ledger.add_to_blacklist(situation)
    ledger.save()

    meta = {
        "episode_id": episode_id,
        "stage": stage,
        "arc": arc,
        "situation": situation,
        "generated_at": datetime.now().isoformat(),
        "content_type": "audio",
        "validation": {
            "vocab_violation_rate": result.vocab.violation_rate,
            "grammar_violations": [t.id for t in result.grammar.violations],
            "comprehension_estimate": result.vocab.comprehension_estimate,
            "attempts_needed": attempt + 1,
        },
        "ledger_delta": delta,
        "total_turns": len(script),
    }

    return AudioEpisode(
        id=episode_id, outline=outline, raw=raw_text,
        script=script, annotated_script=annotated_script, meta=meta)
