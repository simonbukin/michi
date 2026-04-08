"""Sentence length and subordination depth scoring."""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class ComplexityViolation:
    sentence: str
    issue: str  # "sentence_too_long", "subordination_too_deep", "turn_too_long"
    value: int | float
    threshold: int | float


@dataclass
class ComplexityResult:
    passed: bool
    avg_sentence_chars: float
    max_sentence_chars: int
    max_subordination_depth: int
    avg_mora_per_turn: float
    violations: list[ComplexityViolation]


# Sentence-ending patterns for Japanese
SENTENCE_ENDINGS = re.compile(r'[。！？\n]')

# Subordination markers: relative clause, conditional, quotation, nominalization
SUBORDINATION_MARKERS = re.compile(
    r'(?:のが|のを|のは|ので|のに'  # nominalizer clauses
    r'|から|ため|けど|けれど'        # reason/concession
    r'|たら|れば|なら|と(?=[、。])'  # conditionals
    r'|って|と(?=言|思|聞)'          # quotation
    r'|ながら|つつ'                   # simultaneous
    r'|ように|ために)'                # purpose
)

# Rough mora counter: each kana = 1 mora, small kana don't count separately
MORA_PATTERN = re.compile(r'[ぁ-ゔァ-ヴー]')
SMALL_KANA = set('ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ')


def count_mora(text: str) -> int:
    """Count mora in Japanese text (rough estimate)."""
    count = 0
    for ch in text:
        if MORA_PATTERN.match(ch) and ch not in SMALL_KANA:
            count += 1
        elif ch == 'ー':
            count += 1
    return count


def split_sentences(text: str) -> list[str]:
    """Split Japanese text into sentences."""
    parts = SENTENCE_ENDINGS.split(text)
    return [s.strip() for s in parts if s.strip()]


def count_subordination(sentence: str) -> int:
    """Count subordination depth by counting nested clause markers."""
    return len(SUBORDINATION_MARKERS.findall(sentence))


class ComplexityScorer:
    def __init__(self, stage_config: dict):
        self.max_sentence_chars = stage_config.get("max_sentence_chars") or 99999
        self.max_turn_mora = stage_config.get("max_turn_mora") or 99999
        # Subordination depth thresholds by stage
        self.max_sub_depth = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 99999}.get(
            stage_config.get("stage", 6), 99999
        )

    def score(self, text: str, content_type: str = "prose") -> ComplexityResult:
        """Score text complexity. content_type: 'prose' or 'dialogue'."""
        sentences = split_sentences(text)
        violations = []

        if not sentences:
            return ComplexityResult(
                passed=True, avg_sentence_chars=0, max_sentence_chars=0,
                max_subordination_depth=0, avg_mora_per_turn=0, violations=[],
            )

        sentence_lens = [len(s) for s in sentences]
        max_chars = max(sentence_lens)
        avg_chars = sum(sentence_lens) / len(sentence_lens)

        sub_depths = [count_subordination(s) for s in sentences]
        max_sub = max(sub_depths) if sub_depths else 0

        # Check sentence length violations
        for s, length in zip(sentences, sentence_lens):
            if length > self.max_sentence_chars:
                violations.append(ComplexityViolation(
                    sentence=s[:50] + "..." if len(s) > 50 else s,
                    issue="sentence_too_long",
                    value=length,
                    threshold=self.max_sentence_chars,
                ))

        # Check subordination depth
        for s, depth in zip(sentences, sub_depths):
            if depth > self.max_sub_depth:
                violations.append(ComplexityViolation(
                    sentence=s[:50] + "..." if len(s) > 50 else s,
                    issue="subordination_too_deep",
                    value=depth,
                    threshold=self.max_sub_depth,
                ))

        # For dialogue, check mora per turn
        avg_mora = 0.0
        if content_type == "dialogue":
            lines = [l.strip() for l in text.split('\n') if '「' in l]
            if lines:
                mora_counts = [count_mora(l) for l in lines]
                avg_mora = sum(mora_counts) / len(mora_counts)
                for line, mc in zip(lines, mora_counts):
                    if mc > self.max_turn_mora:
                        violations.append(ComplexityViolation(
                            sentence=line[:50] + "..." if len(line) > 50 else line,
                            issue="turn_too_long",
                            value=mc,
                            threshold=self.max_turn_mora,
                        ))

        return ComplexityResult(
            passed=len(violations) == 0,
            avg_sentence_chars=avg_chars,
            max_sentence_chars=max_chars,
            max_subordination_depth=max_sub,
            avg_mora_per_turn=avg_mora,
            violations=violations,
        )
