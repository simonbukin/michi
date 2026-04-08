"""Merge dialogue turns into final MP3 with accumulated timestamps."""

import io
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tts.synthesizer import synthesize_turn
from tts.aligner import align_turn


@dataclass
class AudioPackage:
    mp3: bytes
    timestamps: list[dict]  # [{word, character, start_ms, end_ms}]
    duration_ms: int


def build_episode_audio(script: list, stage_config: dict,
                         characters: dict) -> AudioPackage:
    """Synthesize all turns, align each, merge into final MP3.

    Args:
        script: list of DialogueTurn objects (character, text)
        stage_config: Stage configuration dict
        characters: Character configuration dict

    Returns:
        AudioPackage with MP3 bytes and word-level timestamps
    """
    from pydub import AudioSegment

    audio_segments = []
    all_timestamps = []
    current_offset_ms = 0
    pause_ms = stage_config.get("inter_turn_pause_ms", 1000)

    for turn in script:
        char = turn.character
        text = turn.text
        speaker_id = characters[char]["voice_id"]

        # Synthesize this turn
        wav_bytes = synthesize_turn(
            text=text,
            speaker_id=speaker_id,
            speed_scale=stage_config.get("audio_speed_scale", 1.0),
            intonation_scale=stage_config.get("audio_intonation_scale", 1.0),
        )

        seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))

        # Forced alignment against known text
        word_times = align_turn(wav_bytes, text)

        # Offset timestamps to account for previous turns
        for wt in word_times:
            all_timestamps.append({
                "word": wt.word,
                "character": char,
                "start_ms": wt.start_ms + current_offset_ms,
                "end_ms": wt.end_ms + current_offset_ms,
            })

        audio_segments.append(seg)
        current_offset_ms += len(seg)

        # Inter-turn pause
        pause = AudioSegment.silent(duration=pause_ms)
        audio_segments.append(pause)
        current_offset_ms += pause_ms

    # Merge all segments
    if audio_segments:
        full_audio = audio_segments[0]
        for seg in audio_segments[1:]:
            full_audio += seg
    else:
        full_audio = AudioSegment.empty()

    # Export as MP3
    buf = io.BytesIO()
    full_audio.export(buf, format="mp3", bitrate="128k")
    mp3_bytes = buf.getvalue()

    return AudioPackage(
        mp3=mp3_bytes,
        timestamps=all_timestamps,
        duration_ms=current_offset_ms,
    )
