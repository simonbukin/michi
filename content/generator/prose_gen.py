"""Claude API: Japanese prose/dialogue generation from outline."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Target character counts by stage
TARGET_CHARS = {1: 600, 2: 800, 3: 1000, 4: 1200, 5: 1600, 6: 2000}

PROSE_SYSTEM = """You are a Japanese writer for graded readers.
Write natural, engaging Japanese prose.
Output Japanese text only. No romaji, no English, no commentary.
Do not add titles or headers."""

DIALOGUE_SYSTEM = """You are a Japanese dialogue writer for language learners.
Write natural, engaging Japanese dialogue.
Output only dialogue lines in this format: キャラ名:「セリフ」
No narration, no action descriptions, no stage directions. Pure dialogue only.
No romaji, no English, no commentary."""


def _get_allowed_vocab_sample(ledger_summary: dict, stage_config: dict,
                              max_words: int = 200) -> str:
    """Get a sample of allowed content words for the prompt.

    Loads master vocab, filters by stage, returns top N by frequency
    as a formatted string the LLM can reference.
    """
    from paths import MASTER_VOCAB_PATH
    stage = stage_config.get("stage", 1)

    if not MASTER_VOCAB_PATH.exists():
        return ""

    entries = json.loads(MASTER_VOCAB_PATH.read_text(encoding="utf-8"))
    allowed = [
        e for e in entries
        if e["stage"] <= stage and e.get("freq_rank")
    ]
    allowed.sort(key=lambda e: e["freq_rank"])
    top = allowed[:max_words]

    if not top:
        return ""

    words = [f"{e['kanji']}({e.get('english', '')[:20]})" for e in top]
    return ", ".join(words)


def build_prose_prompt(outline: dict, stage_config: dict,
                        characters: dict, ledger_summary: dict) -> str:
    char_voices = {
        name: data["speech_style"]
        for name, data in characters.items()
        if name in outline.get("characters_in_episode", [])
    }

    stage_num = stage_config.get("stage", 1)

    # Build allowed vocab hint
    vocab_hint = _get_allowed_vocab_sample(ledger_summary, stage_config)
    vocab_section = ""
    if vocab_hint:
        vocab_section = f"""
ALLOWED VOCABULARY (use ONLY these content words and simpler ones):
{vocab_hint}
"""

    return f"""Write a graded reader story from this outline.

OUTLINE:
{json.dumps(outline, ensure_ascii=False, indent=2)}

CHARACTER VOICES:
{json.dumps(char_voices, ensure_ascii=False)}

GRAMMAR CEILING: {stage_config['jlpt']} level — do not use grammar beyond this
TARGET LENGTH: {TARGET_CHARS.get(stage_num, 800)} characters
FURIGANA: do not add — the system adds furigana automatically
TONE: {outline.get('emotional_tone', 'natural')}
{vocab_section}
Write the story now."""


def build_dialogue_prompt(outline: dict, stage_config: dict,
                           characters: dict, ledger_summary: dict) -> str:
    char_voices = {
        name: data["speech_style"]
        for name, data in characters.items()
        if name in outline.get("characters_in_episode", [])
    }

    stage_num = stage_config.get("stage", 1)
    return f"""Write a dialogue from this outline.

OUTLINE:
{json.dumps(outline, ensure_ascii=False, indent=2)}

CHARACTER VOICES:
{json.dumps(char_voices, ensure_ascii=False)}

GRAMMAR CEILING: {stage_config['jlpt']} level — do not use grammar beyond this
TARGET TURNS: {len(outline.get('turns', [])) or 10}
MAX MORA PER TURN: {stage_config.get('max_turn_mora', 30)}
FORMAT: キャラ名:「セリフ」(one turn per line)
TONE: {outline.get('emotional_tone', 'natural')}

Write the dialogue now."""


def generate_prose(client, outline: dict, stage_config: dict,
                    characters: dict, ledger_summary: dict,
                    content_type: str = "reader",
                    model: str = "claude-sonnet-4-20250514") -> str:
    """Generate Japanese prose or dialogue from an outline.

    Returns:
        Raw Japanese text
    """
    if content_type == "audio":
        system = DIALOGUE_SYSTEM
        prompt = build_dialogue_prompt(outline, stage_config, characters, ledger_summary)
    else:
        system = PROSE_SYSTEM
        prompt = build_prose_prompt(outline, stage_config, characters, ledger_summary)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()
