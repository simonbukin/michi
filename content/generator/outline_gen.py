"""Claude API: JSON outline generation for episodes."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROSE_SYSTEM_PROMPT = """You are an outline writer for Japanese graded readers.
Your outlines are used by a separate prose writer.
Output valid JSON only. No commentary, no markdown, no explanation."""

DIALOGUE_SYSTEM_PROMPT = """You are an outline writer for Japanese audio dialogue episodes.
Your outlines are used by a separate dialogue writer.
Output valid JSON only. No commentary, no markdown, no explanation."""


def build_prose_outline_prompt(stage_config: dict, ledger_summary: dict,
                                characters: dict, situation: str,
                                arc: str) -> str:
    return f"""Generate a graded reader episode outline.

STAGE: {stage_config['jlpt']}
SITUATION: {situation}
ARC: {arc}
CHARACTERS AVAILABLE: {json.dumps(list(characters.keys()), ensure_ascii=False)}
NEW VOCABULARY TO INTRODUCE: {json.dumps(ledger_summary['new_words_allocated'], ensure_ascii=False)}
WORDS TO REINFORCE (acquisition zone): {json.dumps(ledger_summary['zone_words'][:10], ensure_ascii=False)}

Output JSON in exactly this structure:
{{
  "title": "short episode title in Japanese",
  "characters_in_episode": ["character names"],
  "setting": "brief description",
  "beat_1": "what happens first",
  "beat_2": "what develops",
  "turn": "small complication or surprising moment",
  "resolution": "how it resolves",
  "emotional_tone": "one word",
  "new_vocab_appears_in": {{
    "word_lemma": "beat_1 or beat_2 or turn or resolution"
  }}
}}"""


def build_dialogue_outline_prompt(stage_config: dict, ledger_summary: dict,
                                   characters: dict, situation: str,
                                   arc: str) -> str:
    return f"""Generate an audio dialogue episode outline.

STAGE: {stage_config['jlpt']}
SITUATION: {situation}
ARC: {arc}
CHARACTERS AVAILABLE: {json.dumps(list(characters.keys()), ensure_ascii=False)}
NEW VOCABULARY TO INTRODUCE: {json.dumps(ledger_summary['new_words_allocated'], ensure_ascii=False)}
WORDS TO REINFORCE (acquisition zone): {json.dumps(ledger_summary['zone_words'][:10], ensure_ascii=False)}

Output JSON in exactly this structure:
{{
  "title": "short episode title in Japanese",
  "characters_in_episode": ["character names"],
  "setting": "brief description",
  "beat_1": "what happens first",
  "beat_2": "what develops",
  "turn": "small complication or surprising moment",
  "resolution": "how it resolves",
  "emotional_tone": "one word",
  "turns": [
    {{"character": "name", "beat": "opening/response/development/turn/resolution", "content": "brief description"}},
  ],
  "aizuchi_moments": ["after beat description"],
  "register_notes": "notes on formality level",
  "new_vocab_appears_in": {{
    "word_lemma": "beat_1 or beat_2 or turn or resolution"
  }}
}}"""


def generate_outline(client, stage_config: dict, ledger_summary: dict,
                      characters: dict, situation: str, arc: str,
                      content_type: str = "reader",
                      model: str = "claude-sonnet-4-20250514") -> dict:
    """Generate an episode outline using Claude API.

    Args:
        client: anthropic.Anthropic client instance
        content_type: 'reader' for prose, 'audio' for dialogue
        model: Claude model to use

    Returns:
        Parsed JSON outline dict
    """
    if content_type == "audio":
        system = DIALOGUE_SYSTEM_PROMPT
        prompt = build_dialogue_outline_prompt(
            stage_config, ledger_summary, characters, situation, arc)
    else:
        system = PROSE_SYSTEM_PROMPT
        prompt = build_prose_outline_prompt(
            stage_config, ledger_summary, characters, situation, arc)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return json.loads(text)
