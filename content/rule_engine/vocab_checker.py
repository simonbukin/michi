"""Hybrid vocabulary validation: MeCab tokenization + longest-match compound lookup.

Uses MeCab for morphological tokenization (handles inflection and word boundaries),
then for each content token, checks the master vocab form index. When a token
isn't found, tries expanding the token's context in the original text to find
compound words (like Yomitan's longest-match behavior).
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import CONFIG_DIR


@dataclass
class VocabViolation:
    surface: str
    lemma: str
    position: int
    stage_required: int | None  # None if word not in any stage
    current_stage: int
    suggestion: str | None = None


@dataclass
class VocabCheckResult:
    passed: bool
    violation_rate: float
    violations: list[VocabViolation]
    comprehension_estimate: float


# POS tags (UniDic) that are exempt from vocabulary checks
EXEMPT_POS = {
    "助詞", "助動詞", "接続詞", "感動詞", "記号",
    "補助記号", "空白", "接尾辞", "接頭辞",
}

# Finer POS categories to exempt
EXEMPT_POS_DETAIL = {
    "固有名詞",    # proper nouns (character names, place names)
    "数詞",        # numerals
    "非自立可能",  # auxiliary/dependent verbs (いる in ている, etc.)
}

# Maximum compound expansion distance (characters left/right of a token)
_MAX_COMPOUND_EXPAND = 5


def _load_character_names() -> set[str]:
    """Load character names from config to exempt from vocab checks."""
    chars_path = CONFIG_DIR / "characters.json"
    if not chars_path.exists():
        return set()
    chars = json.loads(chars_path.read_text(encoding="utf-8"))
    names = set()
    for key, data in chars.items():
        names.add(key)
        if "full_name" in data:
            if isinstance(data["full_name"], list):
                for part in data["full_name"]:
                    names.add(part)
            else:
                names.add(data["full_name"])
    return names


def _katakana_to_hiragana(text: str) -> str:
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return "".join(result)


class VocabChecker:
    def __init__(self, ledger, stage: int):
        self.ledger = ledger
        self.stage = stage
        self._tagger = None
        self._character_names = _load_character_names()

    @property
    def tagger(self):
        if self._tagger is None:
            import fugashi
            self._tagger = fugashi.Tagger()
        return self._tagger

    def _is_content_word(self, node) -> bool:
        """Check if a MeCab node is a content word that should be validated."""
        pos = node.feature.pos1 if hasattr(node.feature, 'pos1') else ""
        if pos in EXEMPT_POS:
            return False
        pos2 = node.feature.pos2 if hasattr(node.feature, 'pos2') else ""
        if pos2 in EXEMPT_POS_DETAIL:
            return False
        if len(node.surface) == 0:
            return False
        return True

    def _get_forms(self, node) -> list[str]:
        """Get all forms to try matching against the ledger.

        Returns multiple forms in priority order:
        - MeCab lemma (kanji dictionary form)
        - surface form
        - kana converted to hiragana
        - orthBase
        """
        forms = []

        if hasattr(node.feature, 'lemma') and node.feature.lemma and node.feature.lemma != '*':
            forms.append(node.feature.lemma)

        forms.append(node.surface)

        if hasattr(node.feature, 'kana') and node.feature.kana and node.feature.kana != '*':
            hira = _katakana_to_hiragana(node.feature.kana)
            if hira not in forms:
                forms.append(hira)

        if hasattr(node.feature, 'orthBase') and node.feature.orthBase and node.feature.orthBase != '*':
            if node.feature.orthBase not in forms:
                forms.append(node.feature.orthBase)

        return forms

    def _is_part_of_allowed_compound(self, surface: str, full_text: str) -> bool:
        """Check if a token is a sub-component of a known compound word.

        Yomitan-style: find all occurrences of this surface in the text,
        then try longest-match expansion to find a compound in the vocab.
        Handles MeCab decomposition like 図書館→図書+館, お弁当→お+弁当.
        """
        start = 0
        while True:
            idx = full_text.find(surface, start)
            if idx == -1:
                break
            # Try expanding: longest substring first (Yomitan style)
            for left in range(max(0, idx - _MAX_COMPOUND_EXPAND), idx + 1):
                for right in range(
                    min(len(full_text), idx + len(surface) + _MAX_COMPOUND_EXPAND),
                    idx + len(surface) - 1,
                    -1,
                ):
                    candidate = full_text[left:right]
                    if len(candidate) > len(surface):
                        if self.ledger.is_allowed(candidate, self.stage):
                            return True
            start = idx + 1
        return False

    def check(self, text: str) -> VocabCheckResult:
        """Check text against the vocabulary ledger.

        Uses MeCab for tokenization, then checks each content token against
        the ledger. If a token isn't found, tries compound expansion in the
        original text (longest-match, like Yomitan).
        """
        nodes = self.tagger(text)
        violations = []
        content_token_count = 0

        for node in nodes:
            if not self._is_content_word(node):
                continue

            content_token_count += 1

            # Skip character names
            if node.surface in self._character_names:
                continue

            # Try all MeCab forms against the ledger
            forms = self._get_forms(node)
            allowed = any(self.ledger.is_allowed(f, self.stage) for f in forms)

            # If not allowed, try compound expansion in original text
            if not allowed:
                allowed = self._is_part_of_allowed_compound(node.surface, text)

            if not allowed:
                lemma = forms[0] if forms else node.surface
                violations.append(VocabViolation(
                    surface=node.surface,
                    lemma=lemma,
                    position=0,
                    stage_required=None,
                    current_stage=self.stage,
                ))

        violation_rate = len(violations) / content_token_count if content_token_count > 0 else 0.0
        return VocabCheckResult(
            passed=violation_rate <= 0.02,
            violation_rate=violation_rate,
            violations=violations,
            comprehension_estimate=1.0 - violation_rate,
        )
