"""Generate Stage 1 episodes — readers (EPUB) and audio (MP3 + HTML transcript).

Stories are written to use only Stage 1 textbook vocabulary. Each is validated
through the mechanical pipeline before export.

Usage (from content/):
    python3.11 generate_batch.py
"""

import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import OUTPUTS_DIR, MASTER_VOCAB_PATH, CONFIG_DIR
from ledger.ledger import VocabLedger
from rule_engine.validator import validate, load_stage_config
from annotator.annotator import annotate
from exporters.epub_exporter import build_epub, render_chapter_html
from exporters.note_curator import curate_notes
from exporters.transcript_exporter import build_transcript_html
from generator.generate_episode import ReaderEpisode, AudioEpisode, DialogueTurn


# ── Stage 1 Reader Episodes ──────────────────────────────────────

READER_EPISODES = [
    {
        "id": "s1_daily_life_ep001",
        "arc": "daily_life",
        "situation": "コンビニで何かを買おうとしている",
        "outline": {
            "title": "コンビニの朝",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "朝のコンビニ",
            "emotional_tone": "楽しい",
        },
        "text": (
            "朝です。あおいはコンビニに行きます。\n\n"
            "コンビニの中は広いです。"
            "食べ物がたくさんあります。"
            "パンもあります。お弁当もあります。\n\n"
            "あおいは「どれがいいかな」と思います。"
            "お弁当は少し高いです。パンは安いです。\n\n"
            "「あ、けんた！」\n\n"
            "けんたもコンビニにいます。"
            "けんたは牛乳を持っています。\n\n"
            "「おはよう。朝ごはん？」とけんたが聞きます。\n\n"
            "「うん。何がいいと思う？」\n\n"
            "「パンがおいしいよ」とけんたが言います。\n\n"
            "あおいはパンを二つ買います。\n\n"
            "外は少し寒いです。"
            "二人はコンビニの前で朝ごはんを食べます。"
            "パンはおいしいです。\n\n"
            "「ありがとう」とあおいが言います。\n\n"
            "いい朝です。"
        ),
    },
    {
        "id": "s1_school_ep001",
        "arc": "school",
        "situation": "図書館で勉強しようとしている",
        "outline": {
            "title": "図書館の午後",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "大学の図書館",
            "emotional_tone": "静か",
        },
        "text": (
            "今日は水曜日です。午後は暇です。\n\n"
            "あおいは図書館に行きます。"
            "勉強しなくてはいけません。\n\n"
            "図書館はとても静かです。"
            "学生がたくさんいます。\n\n"
            "あおいは椅子に座ります。"
            "本を読みます。"
            "でも、少し難しいです。\n\n"
            "「大丈夫？」\n\n"
            "けんたが来ました。\n\n"
            "「この本がわからない」とあおいが言います。\n\n"
            "けんたは椅子に座ります。"
            "「ここを見て」と教えます。\n\n"
            "あおいは「ああ、そうか！」と言います。"
            "わかりました。\n\n"
            "二人は三時間勉強します。"
            "外はもう暗いです。\n\n"
            "「ありがとう。よくわかった」とあおいが言います。"
        ),
    },
    {
        "id": "s1_seasonal_ep001",
        "arc": "seasonal",
        "situation": "花見に行く計画を立てている",
        "outline": {
            "title": "花見の約束",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "学校のベンチ",
            "emotional_tone": "わくわく",
        },
        "text": (
            "四月です。桜がきれいです。\n\n"
            "あおいは学校にいます。"
            "天気がとてもいいです。空が青いです。\n\n"
            "けんたが来ます。\n\n"
            "「見て！桜がきれい！」\n\n"
            "「本当だ。もう春だね」とけんたが言います。\n\n"
            "「土曜日、公園に行きたい！」とあおいが言います。\n\n"
            "「いいね。お弁当を作りましょう」\n\n"
            "あおいはとてもうれしいです。"
            "料理が好きです。\n\n"
            "「飲み物は私が買うよ」とけんたが言います。\n\n"
            "「ありがとう！」\n\n"
            "土曜日が楽しみです。"
        ),
    },
    {
        "id": "s1_social_ep001",
        "arc": "social",
        "situation": "友達と待ち合わせしている",
        "outline": {
            "title": "駅で待つ",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "駅の前",
            "emotional_tone": "ほっとする",
        },
        "text": (
            "日曜日です。あおいは駅の前にいます。"
            "けんたを待っています。\n\n"
            "今日は二人で映画を見ます。"
            "映画は二時からです。\n\n"
            "あおいは時計を見ます。"
            "けんたはまだ来ません。\n\n"
            "「大丈夫かな」と思います。\n\n"
            "すると、けんたが走って来ます。\n\n"
            "「電車が遅かった！」\n\n"
            "「もう！」とあおいが言います。\n\n"
            "「行きましょう！」\n\n"
            "二人は走ります。\n\n"
            "「よかった！」とあおいが言います。\n\n"
            "映画はとてもおもしろいです。"
            "いい日曜日です。"
        ),
    },
]


# ── Stage 1 Audio Episodes (Dialogue) ────────────────────────────

AUDIO_EPISODES = [
    {
        "id": "s1_daily_life_audio001",
        "arc": "daily_life",
        "situation": "朝ごはんを食べながら話している",
        "outline": {
            "title": "朝ごはんの時間",
            "characters_in_episode": ["あおい", "けんた"],
            "emotional_tone": "穏やか",
        },
        "script": [
            DialogueTurn("あおい", "おはよう。"),
            DialogueTurn("けんた", "おはよう。朝ごはん食べた？"),
            DialogueTurn("あおい", "まだ。今から食べるよ。"),
            DialogueTurn("けんた", "何を食べる？"),
            DialogueTurn("あおい", "パンとお茶。"),
            DialogueTurn("けんた", "おいしそうだね。"),
            DialogueTurn("あおい", "けんたは？"),
            DialogueTurn("けんた", "私はもう食べた。"),
            DialogueTurn("あおい", "そうか。今日は何をする？"),
            DialogueTurn("けんた", "学校に行くよ。"),
            DialogueTurn("あおい", "私も。一緒に行きましょう。"),
            DialogueTurn("けんた", "いいね。行きましょう。"),
        ],
    },
    {
        "id": "s1_school_audio001",
        "arc": "school",
        "situation": "授業の前に話している",
        "outline": {
            "title": "授業の前",
            "characters_in_episode": ["あおい", "けんた"],
            "emotional_tone": "日常",
        },
        "script": [
            DialogueTurn("あおい", "今日の授業は何？"),
            DialogueTurn("けんた", "日本語の授業だよ。"),
            DialogueTurn("あおい", "ああ、そうか。"),
            DialogueTurn("けんた", "本を持ってきた？"),
            DialogueTurn("あおい", "あ、忘れた！"),
            DialogueTurn("けんた", "大丈夫。一緒に見ましょう。"),
            DialogueTurn("あおい", "ありがとう！"),
            DialogueTurn("けんた", "授業は何時から？"),
            DialogueTurn("あおい", "十時からだよ。"),
            DialogueTurn("けんた", "もうすぐだね。行きましょう。"),
        ],
    },
]


def generate_readers(ledger, stage, stage_config):
    """Generate reader EPUB episodes."""
    print("=" * 60)
    print("READER EPISODES")
    print("=" * 60)

    all_episodes = []

    for ep_data in READER_EPISODES:
        ep_id = ep_data["id"]
        print(f"\n── {ep_id}: {ep_data['outline']['title']} ──")

        text = ep_data["text"]

        # Validate
        result = validate(text, stage, "prose", ledger)
        print(f"  Validation: passed={result.passed}, "
              f"vocab_rate={result.vocab.violation_rate:.3f}, "
              f"violations={len(result.vocab.violations)}")

        if result.vocab.violations:
            for v in result.vocab.violations[:5]:
                print(f"    vocab: {v.surface} ({v.lemma})")

        if result.grammar.violations:
            for v in result.grammar.violations[:3]:
                print(f"    grammar: {v.id} (stage {v.stage})")

        # Annotate
        ann = annotate(text, stage, ledger, stage_config.get("furigana_threshold", 8))
        glossed = [t for t in ann.tokens if t.gloss]
        print(f"  Annotation: {len(ann.tokens)} tokens, {len(glossed)} glossed")

        # Curate notes (mechanical fallback — no LLM client passed)
        curated = curate_notes(ann, stage)
        print(f"  Notes: {len(curated.vocab)} vocab, {len(curated.grammar)} grammar highlights")

        # Record in ledger
        lemmas = [t.lemma for t in ann.tokens]
        ledger.record_episode(lemmas, ep_id)

        meta = {
            "episode_id": ep_id,
            "stage": stage,
            "arc": ep_data["arc"],
            "situation": ep_data["situation"],
            "generated_at": datetime.now().isoformat(),
            "content_type": "reader",
            "validation": {
                "vocab_violation_rate": result.vocab.violation_rate,
                "comprehension_estimate": result.vocab.comprehension_estimate,
            },
        }

        episode = ReaderEpisode(
            id=ep_id, outline=ep_data["outline"],
            raw=text, annotated=ann, meta=meta,
            curated_notes=curated,
        )
        all_episodes.append(episode)

    # Write individual EPUBs
    for ep in all_episodes:
        epub_bytes = build_epub([ep], stage)
        out_dir = OUTPUTS_DIR / f"stage{stage}" / "readers" / f"arc_{ep.meta['arc']}"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{ep.id}.epub"
        path.write_bytes(epub_bytes)
        print(f"\n  Written: {path} ({len(epub_bytes):,} bytes)")

    # Combined EPUB
    combined = build_epub(all_episodes, stage, "道 — Stage 1 Readers")
    combined_path = OUTPUTS_DIR / f"stage{stage}" / "readers" / "stage1_all_readers.epub"
    combined_path.write_bytes(combined)
    print(f"  Combined: {combined_path} ({len(combined):,} bytes)")

    return all_episodes


def generate_audio(ledger, stage, stage_config):
    """Generate audio episodes (MP3 + HTML transcript)."""
    print("\n" + "=" * 60)
    print("AUDIO EPISODES")
    print("=" * 60)

    characters = json.loads((CONFIG_DIR / "characters.json").read_text(encoding="utf-8"))

    for ep_data in AUDIO_EPISODES:
        ep_id = ep_data["id"]
        print(f"\n── {ep_id}: {ep_data['outline']['title']} ──")

        script = ep_data["script"]

        # Validate the full dialogue text
        full_text = "\n".join(f"{t.character}:「{t.text}」" for t in script)
        result = validate(full_text, stage, "dialogue", ledger)
        print(f"  Validation: passed={result.passed}, "
              f"vocab_rate={result.vocab.violation_rate:.3f}")

        if result.vocab.violations:
            for v in result.vocab.violations[:5]:
                print(f"    vocab: {v.surface} ({v.lemma})")

        # Annotate each turn
        annotated_turns = []
        for turn in script:
            ann = annotate(turn.text, stage, ledger, stage_config.get("furigana_threshold", 8))
            annotated_turns.append(ann)

        # Synthesize audio
        print("  Synthesizing audio...")
        from tts.synthesizer import synthesize_turn as synth
        from pydub import AudioSegment

        audio_segments = []
        all_timestamps = []
        current_offset_ms = 0
        pause_ms = stage_config.get("inter_turn_pause_ms", 1500)

        for turn in script:
            char_name = turn.character
            speaker_id = characters.get(char_name, {}).get("voice_id", 888753760)

            try:
                wav_bytes = synth(
                    text=turn.text,
                    speaker_id=speaker_id,
                    speed_scale=stage_config.get("audio_speed_scale", 0.45),
                    intonation_scale=stage_config.get("audio_intonation_scale", 1.2),
                )
            except Exception as e:
                print(f"    TTS error for '{turn.text}': {e}")
                continue

            seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))

            # Simple word-level timestamps (estimated from segment duration)
            # Forced alignment with stable-whisper would be better but requires
            # the model download. This gives approximate word boundaries.
            words_in_turn = list(turn.text)
            word_duration = len(seg) / max(len(words_in_turn), 1)
            for i, ch in enumerate(words_in_turn):
                all_timestamps.append({
                    "word": ch,
                    "character": char_name,
                    "start_ms": int(current_offset_ms + i * word_duration),
                    "end_ms": int(current_offset_ms + (i + 1) * word_duration),
                })

            audio_segments.append(seg)
            current_offset_ms += len(seg)

            # Inter-turn pause
            pause = AudioSegment.silent(duration=pause_ms)
            audio_segments.append(pause)
            current_offset_ms += pause_ms

            print(f"    {char_name}: {turn.text} ({len(seg)}ms)")

        if not audio_segments:
            print("  No audio generated, skipping.")
            continue

        # Merge and export MP3
        full_audio = audio_segments[0]
        for seg in audio_segments[1:]:
            full_audio += seg

        out_dir = OUTPUTS_DIR / f"stage{stage}" / "audio" / f"arc_{ep_data['arc']}"
        out_dir.mkdir(parents=True, exist_ok=True)

        mp3_path = out_dir / f"{ep_id}.mp3"
        full_audio.export(str(mp3_path), format="mp3", bitrate="128k")
        print(f"\n  MP3: {mp3_path} ({mp3_path.stat().st_size:,} bytes, "
              f"{len(full_audio)}ms)")

        # Build HTML transcript
        class AudioPkg:
            pass
        pkg = AudioPkg()
        pkg.timestamps = all_timestamps
        pkg.duration_ms = current_offset_ms

        html = build_transcript_html(
            pkg, annotated_turns, ep_id, ep_data["outline"]["title"])

        html_path = out_dir / f"{ep_id}_transcript.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"  HTML: {html_path}")

        # Write meta
        meta = {
            "episode_id": ep_id,
            "stage": stage,
            "arc": ep_data["arc"],
            "generated_at": datetime.now().isoformat(),
            "content_type": "audio",
            "total_turns": len(script),
            "duration_ms": int(current_offset_ms),
        }
        meta_path = out_dir / f"{ep_id}_meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    stage = 1
    stage_config = load_stage_config(stage)

    # Initialize ledger from master vocab (stage 1 words as "zone")
    ledger = VocabLedger()
    if not MASTER_VOCAB_PATH.exists():
        print(f"ERROR: {MASTER_VOCAB_PATH} not found.")
        print("Run: cd shared/vocab && python3.11 build_master_vocab.py")
        sys.exit(1)
    master_vocab = json.loads(MASTER_VOCAB_PATH.read_text(encoding="utf-8"))
    for entry in master_vocab:
        if entry["stage"] == 1:
            ledger.words[entry["kanji"]] = {
                "count": 5,
                "status": "zone",
                "stage_introduced": 1,
                "last_seen_episode": "seed",
            }
    ledger._rebuild_form_index()
    print(f"Ledger: {len(ledger.words)} words, {len(ledger._form_index)} indexed forms\n")

    # Generate readers
    generate_readers(ledger, stage, stage_config)

    # Generate audio
    generate_audio(ledger, stage, stage_config)

    # Save ledger
    ledger.save()
    print(f"\nLedger saved: {len(ledger.words)} words tracked")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
