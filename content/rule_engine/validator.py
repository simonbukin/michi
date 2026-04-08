"""Combined validation runner orchestrating vocab, grammar, and complexity checks."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import CONFIG_DIR

from rule_engine.vocab_checker import VocabChecker, VocabCheckResult
from rule_engine.grammar_tagger import GrammarTagger, GrammarCheckResult
from rule_engine.complexity_scorer import ComplexityScorer, ComplexityResult


@dataclass
class ValidationResult:
    passed: bool
    vocab: VocabCheckResult
    grammar: GrammarCheckResult
    complexity: ComplexityResult
    hard_fail: bool   # vocab violation_rate > 0.02 or grammar violation
    soft_fail: bool   # only complexity violations


def load_stage_config(stage: int) -> dict:
    """Load stage configuration from stages.json."""
    stages_path = CONFIG_DIR / "stages.json"
    stages = json.loads(stages_path.read_text(encoding="utf-8"))
    config = stages[str(stage)]
    config["stage"] = stage
    return config


def validate(text: str, stage: int, content_type: str, ledger,
             chapter: int | None = None) -> ValidationResult:
    """Run all validation checks on generated text.

    Args:
        text: Japanese text to validate
        stage: Michi stage number (1-6)
        content_type: 'prose' or 'dialogue'
        ledger: VocabLedger instance
        chapter: Optional chapter number for chapter-level grammar gating

    Returns:
        ValidationResult with combined pass/fail status
    """
    stage_config = load_stage_config(stage)

    # Vocabulary check
    vocab_checker = VocabChecker(ledger, stage)
    vocab_result = vocab_checker.check(text)

    # Grammar check (with optional chapter-level gating)
    grammar_tagger = GrammarTagger()
    grammar_result = grammar_tagger.check(text, stage, chapter=chapter)

    # Complexity check
    complexity_scorer = ComplexityScorer(stage_config)
    complexity_result = complexity_scorer.score(text, content_type)

    hard_fail = not vocab_result.passed or not grammar_result.passed
    soft_fail = not hard_fail and not complexity_result.passed

    return ValidationResult(
        passed=not hard_fail and not soft_fail,
        vocab=vocab_result,
        grammar=grammar_result,
        complexity=complexity_result,
        hard_fail=hard_fail,
        soft_fail=soft_fail,
    )
