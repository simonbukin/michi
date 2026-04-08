"""Map grammar tags from the tagger to token spans."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rule_engine.grammar_tagger import GrammarTagger, GrammarTag


class GrammarNoter:
    """Map grammar pattern matches back to token spans."""

    def __init__(self):
        self.tagger = GrammarTagger()

    def annotate_tokens(self, text: str, tokens: list) -> list[GrammarTag]:
        """Find grammar patterns and assign tags to participating tokens.

        Returns deduplicated list of grammar patterns found.
        """
        all_tags = self.tagger.tag_all(text)

        # Build character offset map for tokens
        token_offsets = []
        offset = 0
        for token in tokens:
            token_offsets.append((offset, offset + len(token.surface)))
            offset += len(token.surface)

        # Map each grammar tag to token indices
        seen_patterns = {}
        for tag in all_tags:
            tag_start, tag_end = tag.span
            for i, (tok_start, tok_end) in enumerate(token_offsets):
                # Token overlaps with grammar pattern span
                if tok_start < tag_end and tok_end > tag_start:
                    tokens[i].grammar_tags.append(tag)

            # Deduplicate by pattern id
            if tag.id not in seen_patterns:
                seen_patterns[tag.id] = tag

        return list(seen_patterns.values())
