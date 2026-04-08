"""Vocabulary ledger — central state for the content generation pipeline."""

import json
from datetime import datetime
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import VOCAB_LEDGER_PATH, MASTER_VOCAB_PATH


def _katakana_to_hiragana(text: str) -> str:
    """Convert katakana to hiragana."""
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return "".join(result)


class VocabLedger:
    """Tracks every Japanese word the learner has encountered and how many times.

    Word status transitions:
        not_seen -> new (first appearance)
        new -> zone (count >= 3)
        zone -> active (count >= 10)

    The ledger uses canonical lemma keys (the master vocab's kanji field).
    A form index maps all known surface/reading/kanji forms back to
    canonical lemmas so that MeCab output can be matched regardless
    of which form MeCab produces.
    """

    def __init__(self, path: Path | None = None):
        self.path = path or VOCAB_LEDGER_PATH
        self.meta = {
            "current_stage": 1,
            "total_episodes_generated": 0,
            "total_characters_generated": 0,
            "last_updated": None,
        }
        self.words: dict[str, dict] = {}
        self.episode_blacklist: list[str] = []
        # Maps any known form → canonical lemma key in self.words
        self._form_index: dict[str, str] = {}
        # Maps canonical lemma → stage from master vocab
        self._stage_map: dict[str, int] = {}
        # Master vocab entries indexed by canonical lemma
        self._master_entries: dict[str, dict] = {}

    def load(self) -> None:
        """Load ledger from disk. Creates empty ledger if file doesn't exist."""
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.meta = data.get("meta", self.meta)
            self.words = data.get("words", {})
            self.episode_blacklist = data.get("episode_blacklist", [])
        self._rebuild_form_index()

    def save(self) -> None:
        """Persist ledger to disk."""
        self.meta["last_updated"] = datetime.now().isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "meta": self.meta,
            "words": self.words,
            "episode_blacklist": self.episode_blacklist,
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _rebuild_form_index(self) -> None:
        """Build form→canonical_lemma index from master_vocab.json.

        For each vocab entry, the index maps all forms in all_forms
        back to the canonical kanji form. When multiple entries share
        the same form, the entry with the lowest stage wins — this
        ensures sub-words like 弁当 (stage 3) resolve to their
        earliest-stage compound お弁当 (stage 1) if available.
        """
        self._form_index = {}
        self._stage_map = {}
        self._master_entries = {}

        # Index all words already in the ledger by their own key
        for lemma in self.words:
            self._form_index[lemma] = lemma

        # Build index from master vocab
        if MASTER_VOCAB_PATH.exists():
            entries = json.loads(MASTER_VOCAB_PATH.read_text(encoding="utf-8"))
            for entry in entries:
                canonical = entry["kanji"]
                stage = entry["stage"]

                # For stage_map: keep the lowest stage when duplicates exist
                if canonical not in self._stage_map or stage < self._stage_map[canonical]:
                    self._stage_map[canonical] = stage
                    self._master_entries[canonical] = entry

                # Index all forms — prefer the entry with the lowest stage
                all_forms = list(entry.get("all_forms", []))
                reading = entry.get("reading", "")
                if reading:
                    all_forms.append(reading)
                all_forms.append(canonical)

                for form in all_forms:
                    if not form:
                        continue
                    if form not in self._form_index:
                        self._form_index[form] = canonical
                    else:
                        # If this entry has a lower stage, prefer it
                        existing_canonical = self._form_index[form]
                        existing_stage = self._stage_map.get(existing_canonical, 999)
                        if stage < existing_stage:
                            self._form_index[form] = canonical

    def _resolve(self, form: str) -> str | None:
        """Resolve any surface/lemma/reading form to canonical lemma, or None."""
        # Direct lookup
        if form in self._form_index:
            return self._form_index[form]
        # Try hiragana conversion (MeCab kana field is katakana)
        hira = _katakana_to_hiragana(form)
        if hira != form and hira in self._form_index:
            return self._form_index[hira]
        return None

    def _status_for_count(self, count: int) -> str:
        if count >= 10:
            return "active"
        if count >= 3:
            return "zone"
        return "new"

    def get_status(self, form: str) -> str:
        """Returns: 'active' | 'zone' | 'new' | 'unknown'.

        Accepts any known form (kanji lemma, hiragana, surface).
        """
        canonical = self._resolve(form)
        if canonical is None:
            return "unknown"
        entry = self.words.get(canonical)
        if entry is None:
            return "unknown"
        return entry["status"]

    def is_allowed(self, form: str, stage: int) -> bool:
        """True if word is in master vocab AND its stage <= the given stage.

        Accepts any known form (kanji lemma, hiragana, surface).
        """
        canonical = self._resolve(form)
        if canonical is None:
            return False
        # Check stage from master vocab
        word_stage = self._stage_map.get(canonical)
        if word_stage is None:
            # Fall back to ledger entry
            entry = self.words.get(canonical)
            if entry is None:
                return False
            return entry.get("stage_introduced", 999) <= stage
        return word_stage <= stage

    def get_canonical(self, form: str) -> str | None:
        """Resolve a form to its canonical lemma, or None if unknown."""
        return self._resolve(form)

    def get_active_words(self) -> list[str]:
        return [w for w, d in self.words.items() if d["status"] == "active"]

    def get_zone_words(self) -> list[str]:
        return [w for w, d in self.words.items() if d["status"] == "zone"]

    def get_new_words(self) -> list[str]:
        return [w for w, d in self.words.items() if d["status"] == "new"]

    def allocate_new_words(self, n: int, stage: int) -> list[str]:
        """Return n words from master vocab for the given stage, not yet in the ledger.

        Prioritizes high-frequency words (lower freq_rank = more common).
        """
        # Filter master entries by stage, sort by freq_rank
        candidates = [
            e for e in self._master_entries.values()
            if e["stage"] == stage and e["kanji"] not in self.words
        ]
        candidates.sort(
            key=lambda e: e["freq_rank"] if e["freq_rank"] else 999999
        )

        return [e["kanji"] for e in candidates[:n]]

    def record_episode(self, lemmas_seen: list[str], episode_id: str) -> dict:
        """Increment counts, update statuses. Returns delta dict for meta JSON.

        lemmas_seen should be canonical lemma keys (use get_canonical() first).
        """
        delta = {}
        for lemma in lemmas_seen:
            # Resolve to canonical form if possible
            canonical = self._resolve(lemma) or lemma
            before_status = self.get_status(canonical)

            if canonical in self.words:
                self.words[canonical]["count"] += 1
                self.words[canonical]["last_seen_episode"] = episode_id
            else:
                self.words[canonical] = {
                    "count": 1,
                    "status": "new",
                    "stage_introduced": self._stage_map.get(
                        canonical, self.meta["current_stage"]
                    ),
                    "last_seen_episode": episode_id,
                }
                # Also index the new form
                self._form_index[canonical] = canonical

            new_status = self._status_for_count(self.words[canonical]["count"])
            self.words[canonical]["status"] = new_status

            after_status = new_status
            if before_status != after_status or before_status == "unknown":
                delta[canonical] = {
                    "status_before": None if before_status == "unknown" else before_status,
                    "status_after": after_status,
                    "count": self.words[canonical]["count"],
                }

        self.meta["total_episodes_generated"] += 1
        self.meta["total_characters_generated"] += sum(len(l) for l in lemmas_seen)
        return delta

    def get_prompt_summary(self, stage: int, new_words_per_episode: int = 5) -> dict:
        """Compact dict for injection into generation prompts."""
        return {
            "stage": stage,
            "total_active": len(self.get_active_words()),
            "zone_words": self.get_zone_words()[:20],
            "new_words_allocated": self.allocate_new_words(new_words_per_episode, stage),
        }

    def add_to_blacklist(self, situation: str) -> None:
        if situation not in self.episode_blacklist:
            self.episode_blacklist.append(situation)

    def get_blacklist(self) -> list[str]:
        return list(self.episode_blacklist)

    def prune_blacklist(self, keep_last_n: int = 20) -> None:
        if len(self.episode_blacklist) > keep_last_n:
            self.episode_blacklist = self.episode_blacklist[-keep_last_n:]
