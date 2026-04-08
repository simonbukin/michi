"""Self-contained HTML transcript with embedded JS audio player."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TRANSCRIPT_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Hiragino Kaku Gothic Pro", "Noto Sans JP", sans-serif;
    max-width: 700px; margin: 0 auto; padding: 16px;
    background: #fafafa; color: #222;
  }}
  .player {{
    position: sticky; top: 0; background: #fafafa;
    padding: 12px 0; border-bottom: 1px solid #e0e0e0;
    margin-bottom: 20px;
  }}
  audio {{ width: 100%; }}
  .transcript {{ line-height: 2.2; font-size: 1.1em; }}
  .turn {{ margin-bottom: 0.5em; }}
  .word {{
    display: inline-block;
    padding: 1px 0;
    border-radius: 2px;
    cursor: pointer;
    transition: background 0.08s;
    position: relative;
  }}
  .word.active {{ background: #ffe066; }}
  .word.status-new {{ border-bottom: 2px dotted #e67e22; }}
  .word.status-zone {{ border-bottom: 1px dotted #3498db; }}
  .word[data-reading]:hover::before {{
    content: attr(data-reading);
    position: absolute;
    top: -1.4em; left: 50%;
    transform: translateX(-50%);
    font-size: 0.6em; color: #888;
    white-space: nowrap;
    pointer-events: none;
  }}
  .word[data-gloss]:hover::after {{
    content: attr(data-gloss);
    position: absolute;
    bottom: 120%; left: 50%;
    transform: translateX(-50%);
    background: #2c3e50; color: #fff;
    padding: 3px 8px; border-radius: 4px;
    font-size: 0.75em; white-space: nowrap;
    z-index: 100; pointer-events: none;
  }}
  .char-label {{
    display: block;
    font-size: 0.75em; color: #888;
    margin-top: 0.8em; margin-bottom: 0.1em;
  }}
</style>
</head>
<body>

<div class="player">
  <strong>{title}</strong>
  <audio id="audio" controls preload="metadata" src="{audio_file}"></audio>
</div>

<div id="transcript" class="transcript">
  {word_spans}
</div>

<script>
const words = {timestamps_json};
const audio = document.getElementById('audio');
let activeId = null;

function msToSec(ms) {{ return ms / 1000; }}

audio.addEventListener('timeupdate', () => {{
  const ms = audio.currentTime * 1000;
  let found = null;
  for (let i = 0; i < words.length; i++) {{
    if (ms >= words[i].start_ms && ms <= words[i].end_ms) {{
      found = 'w' + i;
      break;
    }}
  }}
  if (found !== activeId) {{
    if (activeId) {{
      const prev = document.getElementById(activeId);
      if (prev) prev.classList.remove('active');
    }}
    if (found) {{
      const el = document.getElementById(found);
      if (el) {{
        el.classList.add('active');
        el.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
      }}
    }}
    activeId = found;
  }}
}});

document.querySelectorAll('.word[data-start]').forEach((el, i) => {{
  el.addEventListener('click', () => {{
    const w = words[i];
    if (w) {{
      audio.currentTime = msToSec(w.start_ms);
      audio.play();
    }}
  }});
}});
</script>
</body>
</html>"""


def _find_token(word: str, annotated_turns: list):
    """Find annotation data for a word across all turns."""
    for ann in annotated_turns:
        for token in ann.tokens:
            if token.surface == word or token.lemma == word:
                return token
    return None


def build_transcript_html(audio_package, annotated_script: list,
                           episode_id: str, episode_title: str) -> str:
    """Build self-contained HTML transcript with synchronized audio player.

    Args:
        audio_package: AudioPackage with timestamps
        annotated_script: list of AnnotatedText objects (one per turn)
        episode_id: Episode ID for the audio filename
        episode_title: Display title

    Returns:
        Complete HTML string
    """
    word_spans = []
    current_char = None

    for i, ts in enumerate(audio_package.timestamps):
        word_id = f"w{i}"
        token = _find_token(ts["word"], annotated_script)

        # Insert character label when speaker changes
        if ts.get("character") != current_char:
            current_char = ts["character"]
            word_spans.append(
                f'<span class="char-label">{current_char}</span>')

        classes = ["word"]
        data_attrs = [
            f'id="{word_id}"',
            f'data-start="{ts["start_ms"]}"',
            f'data-end="{ts["end_ms"]}"',
            f'data-char="{ts.get("character", "")}"',
        ]

        if token:
            classes.append(f"status-{token.status}")
            if token.gloss:
                # Escape quotes in gloss text
                gloss_text = token.gloss.en.replace('"', '&quot;')
                data_attrs.append(f'data-gloss="{gloss_text}"')
            if token.furigana:
                data_attrs.append(f'data-reading="{token.furigana}"')

        word_spans.append(
            f'<span {" ".join(data_attrs)} class="{" ".join(classes)}">'
            f'{ts["word"]}</span>'
        )

    timestamps_json = json.dumps(audio_package.timestamps, ensure_ascii=False)

    return TRANSCRIPT_TEMPLATE.format(
        title=episode_title,
        audio_file=f"{episode_id}.mp3",
        word_spans="\n  ".join(word_spans),
        timestamps_json=timestamps_json,
    )
