"""KOReader-compatible EPUB builder with ruby and compact curated notes."""

import io
import sys
from html import escape as html_escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ebooklib import epub
from exporters.note_curator import CuratedNotes

EPUB_CSS = """body {
    font-family: serif;
    line-height: 1.8;
    font-size: 1em;
}

.story-body {
    margin-bottom: 3em;
}

ruby rt {
    font-size: 0.55em;
    color: #666;
}

.notes-section {
    margin-top: 2em;
    padding-top: 0.8em;
    border-top: 1px solid #ccc;
    font-size: 0.85em;
    color: #333;
    line-height: 1.6;
}

.notes-header {
    font-size: 0.9em;
    font-weight: bold;
    margin-bottom: 0.5em;
}

.notes-line {
    margin: 0.3em 0;
}

.notes-word { font-weight: bold; }
.notes-reading { color: #666; }
.notes-grammar-display { font-weight: bold; }
"""


def render_chapter_html(annotated, curated: CuratedNotes | None = None) -> str:
    """Render annotated text to HTML with furigana and compact curated notes.

    No inline footnote markers — just clean prose with ruby furigana.
    Notes section uses curated highlights (5-8 vocab + 2-3 grammar).
    """
    body_parts = []

    for token in annotated.tokens:
        surface = token.surface
        if token.furigana:
            body_parts.append(f'<ruby>{surface}<rt>{token.furigana}</rt></ruby>')
        else:
            body_parts.append(surface)

    # Compact notes section
    notes_section = ""
    if curated and (curated.vocab or curated.grammar):
        lines = []
        lines.append('<div class="notes-section">')
        lines.append('<p class="notes-header">── ノート ──</p>')

        if curated.vocab:
            vocab_parts = []
            for v in curated.vocab:
                if v.reading:
                    vocab_parts.append(
                        f'<span class="notes-word">{html_escape(v.surface)}</span>'
                        f'（<span class="notes-reading">{html_escape(v.reading)}</span>）'
                        f'{html_escape(v.gloss_en)}'
                    )
                else:
                    vocab_parts.append(
                        f'<span class="notes-word">{html_escape(v.surface)}</span> '
                        f'{html_escape(v.gloss_en)}'
                    )
            lines.append(f'<p class="notes-line">{" ・ ".join(vocab_parts)}</p>')

        if curated.grammar:
            grammar_parts = []
            for g in curated.grammar:
                grammar_parts.append(
                    f'<span class="notes-grammar-display">{html_escape(g.display)}</span> '
                    f'{html_escape(g.explanation)}'
                )
            lines.append(f'<p class="notes-line">{" ・ ".join(grammar_parts)}</p>')

        lines.append('</div>')
        notes_section = "\n".join(lines)

    return (
        '<div class="story-body">' + "".join(body_parts) + '</div>\n'
        + notes_section
    )


def build_epub(episodes: list, stage: int,
                series_title: str = "道") -> bytes:
    """Build an EPUB from a list of ReaderEpisode objects.

    Returns:
        EPUB file as bytes
    """
    book = epub.EpubBook()
    book.set_title(f"{series_title} — Stage {stage}")
    book.set_language("ja")
    book.add_author("道 Project")

    css_item = epub.EpubItem(
        file_name="style/michi.css",
        media_type="text/css",
        content=EPUB_CSS.encode("utf-8"),
    )
    book.add_item(css_item)

    chapters = []
    for ep in episodes:
        curated = getattr(ep, 'curated_notes', None)
        chapter_html = render_chapter_html(ep.annotated, curated=curated)
        title = ep.outline.get("title", ep.id)

        ch = epub.EpubHtml(
            title=title,
            file_name=f"{ep.id}.xhtml",
            lang="ja",
        )
        ch.set_content(f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ja">
<head>
  <title>{title}</title>
  <link rel="stylesheet" href="../style/michi.css" type="text/css"/>
</head>
<body>
  <h2 class="episode-title">{title}</h2>
  {chapter_html}
</body>
</html>""".encode("utf-8"))
        ch.add_item(css_item)
        book.add_item(ch)
        chapters.append(ch)

    book.toc = chapters
    book.spine = ["nav"] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    buf = io.BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()
