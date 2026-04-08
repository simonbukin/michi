"""MeCab morphology-based grammar pattern detection with stage-gated checking.

Uses MeCab/UniDic's cForm (conjugation form) and cType (conjugation type)
fields to detect grammar constructions accurately. This replaces the
previous regex-on-surface approach which couldn't distinguish e.g.
volitional 行こう (cForm=意志推量形) from dictionary-form 思う.

Pattern types:
  - "cform": single token with specific conjugation form
  - "lemma_seq": sequence of token lemmas (with optional POS/cForm constraints)
  - "surface_seq": fixed surface string sequences (for compound expressions)
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PATTERNS_PATH = Path(__file__).resolve().parent / "grammar_patterns.json"


@dataclass
class GrammarTag:
    id: str
    name: str
    display: str
    explanation_en: str
    explanation_ja: str
    stage: int
    span: tuple[int, int]  # character start, end in text


@dataclass
class GrammarCheckResult:
    passed: bool
    violations: list[GrammarTag]  # patterns found above current stage


def _get_attr(feature, attr: str, default: str = "") -> str:
    """Safely get a MeCab feature attribute."""
    val = getattr(feature, attr, None)
    if val is None or val == "*":
        return default
    return val


class GrammarTagger:
    def __init__(self):
        self._patterns = None
        self._tagger = None

    @property
    def tagger(self):
        if self._tagger is None:
            import fugashi
            self._tagger = fugashi.Tagger()
        return self._tagger

    @property
    def patterns(self) -> list[dict]:
        if self._patterns is None:
            if PATTERNS_PATH.exists():
                self._patterns = json.loads(
                    PATTERNS_PATH.read_text(encoding="utf-8")
                )
            else:
                self._patterns = []
        return self._patterns

    def _tokenize(self, text: str) -> list[dict]:
        """Tokenize text and extract morphological features."""
        tokens = []
        offset = 0
        for node in self.tagger(text):
            f = node.feature
            tokens.append({
                "surface": node.surface,
                "lemma": _get_attr(f, "lemma"),
                "pos1": _get_attr(f, "pos1"),
                "pos2": _get_attr(f, "pos2"),
                "cType": _get_attr(f, "cType"),
                "cForm": _get_attr(f, "cForm"),
                "start": offset,
                "end": offset + len(node.surface),
            })
            offset += len(node.surface)
        return tokens

    def _check_pattern(self, pat: dict, tokens: list[dict]) -> list[GrammarTag]:
        """Check a single pattern against tokenized text. Returns all matches."""
        matches = []
        ptype = pat.get("type", "surface_seq")

        if ptype == "cform":
            # Match a single token by conjugation form (and optional constraints)
            target_cform = pat["cform"]
            require_pos1 = pat.get("pos1")
            require_lemma_not = pat.get("lemma_not", [])
            for tok in tokens:
                if target_cform in tok["cForm"]:
                    if require_pos1 and tok["pos1"] != require_pos1:
                        continue
                    if tok["lemma"] in require_lemma_not:
                        continue
                    matches.append(GrammarTag(
                        id=pat["id"], name=pat["name"],
                        display=pat.get("display", pat["name"]),
                        explanation_en=pat["explanation_en"],
                        explanation_ja=pat.get("explanation_ja", ""),
                        stage=pat["stage"],
                        span=(tok["start"], tok["end"]),
                    ))

        elif ptype == "lemma_seq":
            # Match a sequence of tokens by lemma (with optional pos/cForm filters)
            seq = pat["sequence"]
            seq_len = len(seq)
            for i in range(len(tokens) - seq_len + 1):
                matched = True
                for j, constraint in enumerate(seq):
                    tok = tokens[i + j]
                    if "lemma" in constraint and tok["lemma"] != constraint["lemma"]:
                        matched = False
                        break
                    if "pos1" in constraint and tok["pos1"] != constraint["pos1"]:
                        matched = False
                        break
                    if "pos2" in constraint and tok["pos2"] != constraint["pos2"]:
                        matched = False
                        break
                    if "cForm" in constraint and constraint["cForm"] not in tok["cForm"]:
                        matched = False
                        break
                    if "cType" in constraint and constraint["cType"] not in tok["cType"]:
                        matched = False
                        break
                    if "surface" in constraint and tok["surface"] != constraint["surface"]:
                        matched = False
                        break
                if matched:
                    matches.append(GrammarTag(
                        id=pat["id"], name=pat["name"],
                        display=pat.get("display", pat["name"]),
                        explanation_en=pat["explanation_en"],
                        explanation_ja=pat.get("explanation_ja", ""),
                        stage=pat["stage"],
                        span=(tokens[i]["start"], tokens[i + seq_len - 1]["end"]),
                    ))

        elif ptype == "surface_seq":
            # Match fixed surface strings in the raw text
            # (fallback for compound expressions not easily decomposed)
            surface_patterns = pat.get("surfaces", [])
            raw_text = "".join(t["surface"] for t in tokens) if tokens else ""
            for sp in surface_patterns:
                start = 0
                while True:
                    idx = raw_text.find(sp, start)
                    if idx == -1:
                        break
                    matches.append(GrammarTag(
                        id=pat["id"], name=pat["name"],
                        display=pat.get("display", pat["name"]),
                        explanation_en=pat["explanation_en"],
                        explanation_ja=pat.get("explanation_ja", ""),
                        stage=pat["stage"],
                        span=(idx, idx + len(sp)),
                    ))
                    start = idx + 1

        return matches

    def tag_all(self, text: str) -> list[GrammarTag]:
        """Return all grammar patterns found in text regardless of stage."""
        tokens = self._tokenize(text)
        tags = []
        for pat in self.patterns:
            tags.extend(self._check_pattern(pat, tokens))
        return tags

    def check(self, text: str, stage: int,
              chapter: int | None = None) -> GrammarCheckResult:
        """Check text for grammar patterns above the current ceiling.

        If grammar_schedule.json exists AND chapter is provided, uses
        chapter-level gating: a pattern is allowed if its schedule entry
        has (pattern.stage < stage) OR (pattern.stage == stage AND
        pattern.chapter <= chapter).

        Otherwise falls back to stage-level ceiling from stages.json.
        """
        from paths import CONFIG_DIR

        ceiling = self._build_ceiling(CONFIG_DIR, stage, chapter)
        if ceiling is None:
            # Stage 6 with "all" — everything allowed
            return GrammarCheckResult(passed=True, violations=[])

        all_tags = self.tag_all(text)

        # Expand combined ceiling entries to cover individual pattern names
        expanded = set(ceiling)
        if "te_ageru_morau_kureru" in expanded:
            expanded.update(["te_ageru", "te_morau", "te_kureru"])
        if "passive" in expanded:
            expanded.add("passive_rareru")
        if "causative" in expanded:
            expanded.add("causative_saseru")
        if "te_shimau" in expanded:
            expanded.add("te_shimau_colloquial")

        # Handle ichidan potential/passive ambiguity:
        # When potential is allowed but passive_rareru is not, suppress
        # passive_rareru since MeCab can't distinguish them.
        suppress_passive_ambiguity = (
            "potential" in expanded
            and "passive_rareru" not in expanded
        )

        # Handle you_da false positive on ように when ようになる/ようにする is allowed:
        # The you_da surface pattern includes ように which also matches
        # the purpose/change constructions.
        suppress_you_da_ambiguity = (
            ("you_ni_naru" in expanded or "you_ni_suru" in expanded)
            and "you_da" not in expanded
        )

        violations = []
        for t in all_tags:
            if t.name in expanded:
                continue
            if suppress_passive_ambiguity and t.name == "passive_rareru":
                continue
            if suppress_you_da_ambiguity and t.name == "you_da":
                continue
            violations.append(t)

        return GrammarCheckResult(
            passed=len(violations) == 0,
            violations=violations,
        )

    def _build_ceiling(self, config_dir: Path, stage: int,
                       chapter: int | None) -> set[str] | None:
        """Build the set of allowed grammar pattern names.

        Returns None if everything is allowed (stage 6 "all").
        """
        schedule_path = config_dir / "grammar_schedule.json"

        # Try chapter-level schedule first
        if chapter is not None and schedule_path.exists():
            schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
            ceiling = set()
            for pattern_name, entry in schedule.items():
                if pattern_name.startswith("_"):
                    continue
                p_stage = entry["stage"]
                p_chapter = entry["chapter"]
                if p_stage < stage or (p_stage == stage and p_chapter <= chapter):
                    ceiling.add(pattern_name)
            return ceiling

        # Fall back to stage-level ceiling from stages.json
        stages_path = config_dir / "stages.json"
        if stages_path.exists():
            stages = json.loads(stages_path.read_text(encoding="utf-8"))
            config = stages.get(str(stage), {})
            ceiling_list = config.get("grammar_ceiling", [])
            if ceiling_list == "all":
                return None
            return set(ceiling_list)

        return set()
