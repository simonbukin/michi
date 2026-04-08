"""Furigana generation via fugashi + UniDic."""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# Regex to detect kanji characters
KANJI_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')


@dataclass
class AnnotatedToken:
    """A single token with all annotation data."""
    surface: str
    lemma: str
    pos: str
    reading: str | None = None
    furigana: str | None = None
    gloss: object = None  # Set by glosser
    grammar_tags: list = field(default_factory=list)
    status: str = "unknown"  # active/zone/new/unknown
    footnote_id: int | None = None


def katakana_to_hiragana(text: str) -> str:
    """Convert katakana to hiragana."""
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return "".join(result)


def has_kanji(text: str) -> bool:
    return bool(KANJI_RE.search(text))


class FuriganaGenerator:
    """Generate furigana annotations for Japanese text using fugashi/UniDic."""

    def __init__(self, ledger=None, furigana_threshold: int = 8):
        self._tagger = None
        self.ledger = ledger
        self.furigana_threshold = furigana_threshold

    @property
    def tagger(self):
        if self._tagger is None:
            import fugashi
            self._tagger = fugashi.Tagger()
        return self._tagger

    def _should_show_furigana(self, lemma: str, surface: str) -> bool:
        """Determine if furigana should be displayed for this token."""
        if not has_kanji(surface):
            return False
        if self.ledger is None:
            return True
        # Resolve through form index to find canonical entry
        canonical = self.ledger.get_canonical(lemma)
        if canonical is None:
            canonical = self.ledger.get_canonical(surface)
        if canonical is None:
            return True  # Unknown words always get furigana
        entry = self.ledger.words.get(canonical)
        if entry is None:
            return True
        return entry["count"] < self.furigana_threshold

    def tokenize(self, text: str) -> list[AnnotatedToken]:
        """Tokenize text and generate furigana annotations."""
        nodes = self.tagger(text)
        tokens = []

        for node in nodes:
            surface = node.surface
            if not surface:
                continue

            # Extract features from UniDic
            lemma = surface
            pos = ""
            reading = None

            if hasattr(node.feature, 'lemma') and node.feature.lemma and node.feature.lemma != '*':
                lemma = node.feature.lemma
            elif hasattr(node.feature, 'orthBase') and node.feature.orthBase and node.feature.orthBase != '*':
                lemma = node.feature.orthBase

            if hasattr(node.feature, 'pos1'):
                pos = node.feature.pos1
                if hasattr(node.feature, 'pos2') and node.feature.pos2 and node.feature.pos2 != '*':
                    pos = f"{node.feature.pos1}-{node.feature.pos2}"

            if hasattr(node.feature, 'kana') and node.feature.kana and node.feature.kana != '*':
                reading = node.feature.kana
            elif hasattr(node.feature, 'pron') and node.feature.pron and node.feature.pron != '*':
                reading = node.feature.pron

            # Generate furigana
            furigana = None
            if reading and self._should_show_furigana(lemma, surface):
                furigana = katakana_to_hiragana(reading)

            # Determine status from ledger (check both lemma and surface)
            status = "unknown"
            if self.ledger:
                status = self.ledger.get_status(lemma)
                if status == "unknown":
                    status = self.ledger.get_status(surface)

            tokens.append(AnnotatedToken(
                surface=surface,
                lemma=lemma,
                pos=pos,
                reading=reading,
                furigana=furigana,
                status=status,
            ))

        return tokens
