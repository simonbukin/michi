"""Claude API: targeted violation correction."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _find_replacement_candidates(lemma: str, stage: int,
                                  max_candidates: int = 3) -> list[str]:
    """Find allowed vocab words that could replace a violation.

    Looks for words with similar POS or meaning in the allowed pool.
    """
    from paths import MASTER_VOCAB_PATH
    if not MASTER_VOCAB_PATH.exists():
        return []

    import json
    entries = json.loads(MASTER_VOCAB_PATH.read_text(encoding="utf-8"))

    # Find the violated word's entry to get POS
    violated_entry = None
    for e in entries:
        if e["kanji"] == lemma or lemma in e.get("all_forms", []):
            violated_entry = e
            break

    if not violated_entry:
        return []

    violated_pos = set(violated_entry.get("pos", []))

    # Find allowed words with same POS, sorted by frequency
    candidates = []
    for e in entries:
        if e["stage"] > stage:
            continue
        if not e.get("freq_rank"):
            continue
        entry_pos = set(e.get("pos", []))
        if entry_pos & violated_pos:
            candidates.append(e)

    candidates.sort(key=lambda e: e["freq_rank"])
    return [c["kanji"] for c in candidates[:max_candidates]]


def build_correction_prompt(original_text: str, violations: list,
                             stage_config: dict) -> str:
    """Build a correction prompt for vocabulary violations with specific replacements."""
    stage_num = stage_config.get("stage", 1)
    violation_lines = []
    for v in violations:
        candidates = _find_replacement_candidates(v.lemma, stage_num)
        line = (f"- 「{v.surface}」(lemma: {v.lemma}) is "
                f"too advanced for Stage {stage_config['jlpt']}.")
        if candidates:
            line += f" Use instead: {', '.join(f'「{c}」' for c in candidates)}"
        elif v.suggestion:
            line += f" Possible replacement: 「{v.suggestion}」"
        violation_lines.append(line)

    return f"""The following words in this text are too advanced for Stage {stage_config['jlpt']}:

{chr(10).join(violation_lines)}

Original text:
{original_text}

Rewrite only the sentences containing these words.
Replace each flagged word with a natural Stage {stage_config['jlpt']} alternative from the suggestions above.
Do not change any other sentences.
Output the complete corrected text."""


def build_complexity_correction_prompt(original_text: str, violations: list,
                                        stage_config: dict) -> str:
    """Build a correction prompt for complexity violations."""
    issue_lines = []
    for v in violations:
        if v.issue == "sentence_too_long":
            issue_lines.append(
                f"- Sentence too long ({v.value} chars, max {v.threshold}): "
                f"「{v.sentence}」")
        elif v.issue == "subordination_too_deep":
            issue_lines.append(
                f"- Too many nested clauses ({v.value}, max {v.threshold}): "
                f"「{v.sentence}」")
        elif v.issue == "turn_too_long":
            issue_lines.append(
                f"- Dialogue turn too long ({v.value} mora, max {v.threshold}): "
                f"「{v.sentence}」")

    return f"""The following sentences are too complex for Stage {stage_config['jlpt']}:

{chr(10).join(issue_lines)}

Original text:
{original_text}

Simplify only the flagged sentences:
- Split long sentences into shorter ones
- Reduce nested clauses
- Keep the same meaning and vocabulary
Output the complete corrected text."""


def correct_text(client, original_text: str, violations: list,
                  violation_type: str, stage_config: dict,
                  model: str = "claude-sonnet-4-20250514") -> str:
    """Send correction prompt to Claude and return corrected text.

    Args:
        violation_type: 'vocab' or 'complexity'
    """
    if violation_type == "vocab":
        prompt = build_correction_prompt(original_text, violations, stage_config)
    else:
        prompt = build_complexity_correction_prompt(
            original_text, violations, stage_config)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system="You are a Japanese text editor. Output only the corrected Japanese text. No commentary.",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()
