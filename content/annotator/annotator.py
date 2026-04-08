"""Entry point combining all annotation stages."""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from annotator.furigana import FuriganaGenerator, AnnotatedToken
from annotator.glosser import Glosser
from annotator.grammar_noter import GrammarNoter
from rule_engine.grammar_tagger import GrammarTag


@dataclass
class AnnotatedText:
    tokens: list[AnnotatedToken]
    grammar_patterns: list[GrammarTag]
    raw: str
    stage: int


def annotate(text: str, stage: int, ledger, furigana_threshold: int = 8) -> AnnotatedText:
    """Annotate Japanese text with furigana, glosses, and grammar tags.

    Args:
        text: Raw Japanese text
        stage: Michi stage number (1-6)
        ledger: VocabLedger instance
        furigana_threshold: Show furigana for words seen fewer than this many times

    Returns:
        AnnotatedText with all annotation data
    """
    # Step 1: Tokenize + furigana
    furigana_gen = FuriganaGenerator(ledger=ledger, furigana_threshold=furigana_threshold)
    tokens = furigana_gen.tokenize(text)

    # Step 2: Add glosses for new/zone words
    glosser = Glosser()
    glosser.gloss_tokens(tokens, ledger=ledger)

    # Step 3: Grammar pattern annotation
    noter = GrammarNoter()
    grammar_patterns = noter.annotate_tokens(text, tokens)

    return AnnotatedText(
        tokens=tokens,
        grammar_patterns=grammar_patterns,
        raw=text,
        stage=stage,
    )
