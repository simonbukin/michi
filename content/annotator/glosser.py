"""JMDict English gloss lookup via jamdict."""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class Gloss:
    en: str
    pos: str
    notes: str | None = None
    freq_rank: int | None = None


class Glosser:
    """Look up English glosses for Japanese words using jamdict."""

    def __init__(self):
        self._jam = None

    @property
    def jam(self):
        if self._jam is None:
            from jamdict import Jamdict
            self._jam = Jamdict()
        return self._jam

    def lookup(self, lemma: str, pos_hint: str = "") -> Gloss | None:
        """Look up the most common English gloss for a lemma."""
        try:
            result = self.jam.lookup(lemma)
        except Exception:
            return None

        if not result.entries:
            return None

        entry = result.entries[0]

        # Get part of speech from first sense
        pos_tags = []
        if entry.senses:
            for sense in entry.senses:
                for pos in sense.pos:
                    pos_tags.append(str(pos))
                break

        # Get first English gloss
        glosses = []
        for sense in entry.senses:
            for gloss in sense.gloss:
                if hasattr(gloss, 'text'):
                    glosses.append(gloss.text)
                else:
                    glosses.append(str(gloss))
            if glosses:
                break

        if not glosses:
            return None

        return Gloss(
            en="; ".join(glosses[:3]),
            pos=", ".join(pos_tags[:2]) if pos_tags else "",
        )

    # POS categories that should never receive glosses (function words)
    SKIP_POS = {"助詞", "助動詞", "接続助詞", "係助詞", "格助詞", "補助記号", "記号", "空白"}
    # Sub-POS categories to skip (auxiliary verbs/adjectives in compound forms)
    SKIP_POS_SUB = {"非自立可能"}

    def gloss_tokens(self, tokens: list, gloss_statuses: set = None,
                     ledger=None) -> None:
        """Add glosses to tokens in-place. Only glosses content words with matching status.

        If a ledger is provided, populates freq_rank from master vocab entries.
        """
        if gloss_statuses is None:
            gloss_statuses = {"new", "zone"}

        glossed_lemmas = set()
        for token in tokens:
            if token.status not in gloss_statuses:
                continue
            if token.lemma in glossed_lemmas:
                continue
            # Skip function words — they shouldn't receive glosses
            pos_parts = token.pos.split("-") if token.pos else []
            pos_main = pos_parts[0] if pos_parts else ""
            pos_sub = pos_parts[1] if len(pos_parts) > 1 else ""
            if pos_main in self.SKIP_POS or pos_sub in self.SKIP_POS_SUB:
                continue

            gloss = self.lookup(token.lemma, token.pos)
            if gloss:
                # Look up freq_rank from ledger's master entries
                if ledger is not None:
                    canonical = ledger.get_canonical(token.lemma)
                    if canonical and canonical in ledger._master_entries:
                        gloss.freq_rank = ledger._master_entries[canonical].get("freq_rank")
                token.gloss = gloss
                glossed_lemmas.add(token.lemma)
