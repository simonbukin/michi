"""AivisSpeech per-turn WAV synthesis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

AIVIS_BASE_URL = "http://127.0.0.1:10101"


def synthesize_turn(text: str, speaker_id: int,
                    speed_scale: float = 1.0,
                    intonation_scale: float = 1.0,
                    pre_phoneme_length: float = 0.05,
                    post_phoneme_length: float = 0.1) -> bytes:
    """Synthesize a single dialogue turn via AivisSpeech API.

    Args:
        text: Japanese text to synthesize
        speaker_id: AivisSpeech voice ID
        speed_scale: Speech speed multiplier
        intonation_scale: Intonation variation multiplier
        pre_phoneme_length: Silence before speech (seconds)
        post_phoneme_length: Silence after speech (seconds)

    Returns:
        Raw WAV bytes
    """
    # Step 1: Get synthesis parameters
    query_response = requests.post(
        f"{AIVIS_BASE_URL}/audio_query",
        params={"text": text, "speaker": speaker_id},
        timeout=30,
    )
    query_response.raise_for_status()
    query = query_response.json()

    # Override parameters
    query["speedScale"] = speed_scale
    query["intonationScale"] = intonation_scale
    query["prePhonemeLength"] = pre_phoneme_length
    query["postPhonemeLength"] = post_phoneme_length

    # Step 2: Synthesize audio
    synth_response = requests.post(
        f"{AIVIS_BASE_URL}/synthesis",
        params={"speaker": speaker_id},
        json=query,
        timeout=120,
    )
    synth_response.raise_for_status()
    return synth_response.content
