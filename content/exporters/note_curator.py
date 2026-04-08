"""LLM post-pass to select the most useful vocab and grammar highlights from annotations.

Falls back to a mechanical selection (top-N by freq_rank descending) when no LLM client
is available.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class VocabHighlight:
    surface: str
    reading: str  # furigana, may be empty
    gloss_en: str
    freq_rank: int | None = None


@dataclass
class GrammarHighlight:
    display: str  # e.g. "～たい"
    explanation: str  # short natural-language note


@dataclass
class CuratedNotes:
    vocab: list[VocabHighlight] = field(default_factory=list)
    grammar: list[GrammarHighlight] = field(default_factory=list)


def _mechanical_fallback(annotated, stage: int,
                         max_vocab: int = 8, max_grammar: int = 3) -> CuratedNotes:
    """Pick highlights without an LLM — use freq_rank and stage relevance."""
    # Collect unique glossed tokens (new/zone only, first occurrence per lemma)
    seen_lemmas: set[str] = set()
    candidates = []
    for tok in annotated.tokens:
        if not tok.gloss or tok.lemma in seen_lemmas:
            continue
        if tok.status not in ("new", "zone"):
            continue
        seen_lemmas.add(tok.lemma)
        candidates.append(tok)

    # Sort: prefer rarer words (higher freq_rank = less common = more interesting)
    # Words without freq_rank go to the end
    candidates.sort(
        key=lambda t: -(t.gloss.freq_rank or 0)
    )

    vocab = [
        VocabHighlight(
            surface=tok.surface,
            reading=tok.furigana or "",
            gloss_en=tok.gloss.en,
            freq_rank=tok.gloss.freq_rank,
        )
        for tok in candidates[:max_vocab]
    ]

    # Grammar: deduplicate by name, skip very basic patterns
    BASIC_PATTERNS = {"masu_form", "te_form", "nai_form", "ta_form",
                      "basic_particles", "i_adjective", "na_adjective"}
    seen_names: set[str] = set()
    grammar = []
    for pat in annotated.grammar_patterns:
        if pat.name in seen_names or pat.name in BASIC_PATTERNS:
            continue
        seen_names.add(pat.name)
        grammar.append(GrammarHighlight(
            display=pat.display,
            explanation=pat.explanation_en,
        ))
        if len(grammar) >= max_grammar:
            break

    return CuratedNotes(vocab=vocab, grammar=grammar)


CURATOR_PROMPT = """\
You are a Japanese reading assistant. Given annotation data from a stage {stage} \
learner's reading episode, select the most useful highlights for a compact notes section.

Pick 5-8 vocabulary items that are:
- Actually interesting or useful (NOT basic words like 四、の、は、が、です)
- Appropriate for this stage level
- Worth highlighting for a learner

Pick 2-3 grammar patterns that are:
- Worth calling out at this stage (NOT です/ます/basic particles)
- Explained in natural language, not romanized names

Return JSON:
{{
  "vocab": [
    {{"surface": "桜", "reading": "さくら", "gloss_en": "cherry blossom"}}
  ],
  "grammar": [
    {{"display": "～たい", "explanation": "want to do something"}}
  ]
}}

--- Annotation Data ---

Glossed vocabulary:
{vocab_json}

Grammar patterns found:
{grammar_json}
"""


def curate_notes(annotated, stage: int, client=None) -> CuratedNotes:
    """Select highlights from annotation data.

    Args:
        annotated: AnnotatedText with tokens and grammar_patterns
        stage: Current michi stage (1-6)
        client: Optional anthropic.Anthropic client for LLM curation

    Returns:
        CuratedNotes with selected vocab and grammar highlights
    """
    if client is None:
        return _mechanical_fallback(annotated, stage)

    # Build annotation summary for the LLM
    seen_lemmas: set[str] = set()
    vocab_data = []
    for tok in annotated.tokens:
        if not tok.gloss or tok.lemma in seen_lemmas:
            continue
        if tok.status not in ("new", "zone"):
            continue
        seen_lemmas.add(tok.lemma)
        vocab_data.append({
            "surface": tok.surface,
            "reading": tok.furigana or "",
            "gloss_en": tok.gloss.en,
            "freq_rank": tok.gloss.freq_rank,
            "status": tok.status,
        })

    grammar_data = []
    seen_names: set[str] = set()
    for pat in annotated.grammar_patterns:
        if pat.name in seen_names:
            continue
        seen_names.add(pat.name)
        grammar_data.append({
            "display": pat.display,
            "name": pat.name,
            "explanation_en": pat.explanation_en,
        })

    prompt = CURATOR_PROMPT.format(
        stage=stage,
        vocab_json=json.dumps(vocab_data, ensure_ascii=False, indent=2),
        grammar_json=json.dumps(grammar_data, ensure_ascii=False, indent=2),
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())

        vocab = [
            VocabHighlight(
                surface=v["surface"],
                reading=v.get("reading", ""),
                gloss_en=v["gloss_en"],
            )
            for v in data.get("vocab", [])
        ]
        grammar = [
            GrammarHighlight(
                display=g["display"],
                explanation=g["explanation"],
            )
            for g in data.get("grammar", [])
        ]
        return CuratedNotes(vocab=vocab, grammar=grammar)

    except Exception as e:
        print(f"  Note curation LLM call failed ({e}), using mechanical fallback")
        return _mechanical_fallback(annotated, stage)
