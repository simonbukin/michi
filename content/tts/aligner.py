"""Forced alignment using stable-whisper for word-level timestamps."""

import io
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_model = None


@dataclass
class WordTimestamp:
    word: str
    start_ms: int
    end_ms: int


def get_model():
    """Lazy-load the stable-whisper model."""
    global _model
    if _model is None:
        import stable_whisper
        # "base" is sufficient for clean synthesized audio
        _model = stable_whisper.load_model("base")
    return _model


def align_turn(wav_bytes: bytes, known_text: str) -> list[WordTimestamp]:
    """Forced alignment of known_text against wav_bytes.

    Args:
        wav_bytes: Raw WAV audio bytes
        known_text: The exact Japanese text that was synthesized

    Returns:
        Word-level timestamps
    """
    model = get_model()

    # Write WAV to a temp file (stable-whisper needs a file path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        tmp_path = f.name

    try:
        result = model.align(
            tmp_path,
            known_text,
            language="ja",
        )

        timestamps = []
        for segment in result.segments:
            for word in segment.words:
                timestamps.append(WordTimestamp(
                    word=word.word.strip(),
                    start_ms=int(word.start * 1000),
                    end_ms=int(word.end * 1000),
                ))
        return timestamps
    finally:
        Path(tmp_path).unlink(missing_ok=True)
