"""Validate and constraint-fix the 5 Stage 2 Ch.1 reader episodes.

Runs each episode through the validate→correct loop using claude -p.
Outputs corrected text and builds EPUBs.

Usage (from content/):
    python3.11 fix_stage2_ch1.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import OUTPUTS_DIR, MASTER_VOCAB_PATH, CONFIG_DIR
from ledger.ledger import VocabLedger
from rule_engine.validator import validate, load_stage_config
from annotator.annotator import annotate
from exporters.epub_exporter import build_epub
from exporters.note_curator import curate_notes
from generator.generate_episode import ReaderEpisode
from generator.correction_gen import correct_text
from generator.claude_backend import ClaudeCodeClient


EPISODES = [
    {
        "id": "s2_ch01_daily_life_ep001",
        "title": "作れるかな？",
        "arc": "daily_life",
        "situation": "料理が苦手なあおいが自分で料理を作る",
        "text": (
            "あおいは今日、料理をしたいと思いました。でも、あおいはあまり料理が得意ではありません。"
            "いつもコンビニのご飯を食べていますが、今日は自分で作りたいと思いました。\n\n"
            "「何が作れるかな」と、あおいは思いました。冷蔵庫を開けました。"
            "卵と野菜と豆腐がありました。でも、何を作るかわかりませんでした。\n\n"
            "「卵は使えるし、野菜も切れる。でも、難しいものは作れないな」とあおいは思いました。\n\n"
            "あおいはけんたに電話をしました。\n\n"
            "「けんた、料理の作り方を教えてください！」\n\n"
            "「いいよ。何が作れる？」とけんたが聞きました。\n\n"
            "「卵は使えると思う。野菜も切れるよ。でも、難しいものは作れない」とあおいが言いました。\n\n"
            "「じゃあ、野菜炒めはどう？簡単に作れるよ。まず、野菜を切ります。"
            "それから、フライパンに油を入れて、野菜を炒めます。最後に塩と醤油を入れます」"
            "とけんたが言いました。\n\n"
            "「わかった。できると思う！やってみます！」\n\n"
            "電話を切って、あおいは料理を始めました。野菜をきれいに切ることができました。"
            "フライパンで炒めることもできました。しかし、醤油を入れすぎました。"
            "味がとても濃くなりました。\n\n"
            "「うーん、少し濃すぎる…。でも、食べられるよ！」\n\n"
            "あおいはひとりで野菜炒めを全部食べました。おいしくはなかったですが、"
            "自分で料理ができて、とてもうれしかったです。\n\n"
            "夜、けんたにメッセージを送りました。「野菜炒めを作ることができた！"
            "でも、醤油を入れすぎた。次はもっと上手に作れると思う！」\n\n"
            "けんたから返事が来ました。「よかった！もっと練習してください。きっと上手に作れるよ」"
        ),
    },
    {
        "id": "s2_ch01_school_ep001",
        "title": "何語が話せる？",
        "arc": "school",
        "situation": "話せる言語や読める漢字について話す",
        "text": (
            "けんたとあおいは大学の食堂でお昼ご飯を食べています。\n\n"
            "「ねえ、けんた。中国語が話せる？」とあおいが聞きました。\n\n"
            "「少し話せるよ。でも、あまり上手じゃない。"
            "文字は少し読めるけど、書くのは難しいな」とけんたが言いました。\n\n"
            "「そうか。私は中国語が全然話せない。英語は少し話せるけど…」\n\n"
            "「あおいは英語が得意じゃないの？」\n\n"
            "「読めるし、書けるよ。でも、話すのが苦手。"
            "外国人と話せないと思う」とあおいが言いました。\n\n"
            "「大丈夫だよ。一緒に練習しましょう。きっと話せるよ」\n\n"
            "「本当に？うれしい！ありがとう」\n\n"
            "二人は英語で少し話しました。最初は難しかったですが、少し話せました。\n\n"
            "その後、あおいは難しい漢字をノートに書いていました。\n\n"
            "「ねえ、けんた。この漢字が読める？」とあおいは聞きました。\n\n"
            "「うーん、読めないな。難しい字だね。何の漢字？」\n\n"
            "「授業で出てきた。先生の説明が聞こえなかったから、わからなかった」"
            "とあおいが言いました。\n\n"
            "「スマホで調べることができるよ」とけんたが言いました。\n\n"
            "けんたはスマホで漢字を調べました。「これは『憂鬱』と読む。難しい字だね」\n\n"
            "「そうか。でも、この字は難しすぎて、私には書けない」とあおいが言いました。\n\n"
            "「毎日練習してください。きっと書けるよ」\n\n"
            "「そうだね。けんたは漢字が全部書ける？」\n\n"
            "「全部は書けないよ。でも、よく使う漢字は書けると思う。"
            "難しい字はやっぱり書けないな」とけんたが言いました。\n\n"
            "「じゃあ、一緒に漢字の練習をしましょう！"
            "毎日少しずつ練習したいと思う」とあおいが言いました。"
        ),
    },
    {
        "id": "s2_ch01_daily_life_ep002",
        "title": "休みの日の計画",
        "arc": "daily_life",
        "situation": "土曜日に出かける計画を立てる",
        "text": (
            "あおいとけんたは今週の土曜日に一緒に出かけたいと思っています。\n\n"
            "「どこへ行きましょうか」とあおいが聞きました。\n\n"
            "「駅の近くに新しい公園がある。散歩できるよ」とけんたが言いました。\n\n"
            "「いいね！あの公園でピクニックができる？」\n\n"
            "「できると思うよ。芝生でお弁当も食べられるよ」とけんたが言いました。\n\n"
            "「じゃあ、お弁当を持って行きましょう。他に何ができる？」\n\n"
            "「公園の隣に図書館がある。本が借りられるよ」とけんたが言いました。\n\n"
            "「いいね。あと、近くにカフェはある？」\n\n"
            "「あるよ。コーヒーが飲めるし、ケーキも食べられるよ」とけんたが言いました。\n\n"
            "「最高だね！電車で行ける？」とあおいが聞きました。\n\n"
            "「うん、駅から歩いて行けるよ。バスでも行けると思う」とけんたが言いました。\n\n"
            "「じゃあ、何時に会えますか？」\n\n"
            "「九時はどう？九時に駅で会えるよ」とけんたが言いました。\n\n"
            "「いいね。けんた、お弁当が作れる？」とあおいが聞きました。\n\n"
            "「作れるよ！おにぎりと卵焼きを作ります。あおいは何か持って来られる？」\n\n"
            "「飲み物を持って来られるよ。お茶を買って行きます」とあおいが言いました。\n\n"
            "「ありがとう。土曜日が楽しみだね！いい天気になってほしいな」"
            "とあおいが言いました。\n\n"
            "「そうだね。晴れると思うよ。いい日になると思う」とけんたが言いました。\n\n"
            "「土曜日まで待ちきれない！早く来てほしいな」とあおいが言いました。"
        ),
    },
    {
        "id": "s2_ch01_social_ep001",
        "title": "アルバイトの初日",
        "arc": "social",
        "situation": "カフェのアルバイト初日で自分ができる仕事に挑戦する",
        "text": (
            "今日はあおいのアルバイトの初日です。あおいはカフェで働きます。"
            "少し緊張しています。\n\n"
            "店長の田中さんが仕事を説明しました。\n\n"
            "「あおいさん、コーヒーを作ることができますか？」と田中さんが聞きました。\n\n"
            "「少しできると思います。でも、まだ上手じゃないです」とあおいが言いました。\n\n"
            "「大丈夫ですよ。レジは使えますか？」\n\n"
            "「はい、使えます。前のアルバイトでレジを使っていたので、大丈夫です」"
            "とあおいが言いました。\n\n"
            "「よかった。お客さんに料理を運べますか？」\n\n"
            "「はい、運べます」とあおいが言いました。\n\n"
            "「外国のお客さんも来ます。英語のメニューが読めますか？」と田中さんが聞きました。\n\n"
            "「少し読めます。でも、難しい英語は読めないと思います」とあおいが言いました。\n\n"
            "「大丈夫ですよ。メニューの英語は簡単です。読めると思います」"
            "と田中さんが言いました。\n\n"
            "「ありがとうございます。がんばります！」\n\n"
            "午後、外国のお客さんが来ました。あおいは英語でメニューを説明しました。"
            "緊張しましたが、ちゃんと話せました。\n\n"
            "お客さんは「Thank you!」と言いました。あおいはとてもうれしかったです。"
            "「英語でも話せた！」と心の中で思いました。\n\n"
            "夕方、田中さんはあおいに言いました。「今日はよく働きました。"
            "レジも上手に使えましたね。英語も話せましたね」\n\n"
            "「ありがとうございます。コーヒーはまだ上手に作れませんが、"
            "練習したいと思います」とあおいが言いました。\n\n"
            "「毎日練習してください。きっと上手に作れるよ」と田中さんが言いました。\n\n"
            "「はい！明日もがんばります！」とあおいが言いました。"
        ),
    },
    {
        "id": "s2_ch01_seasonal_ep001",
        "title": "雨の日に何ができる？",
        "arc": "seasonal",
        "situation": "雨で外に出られない日に図書館で過ごす",
        "text": (
            "今日は雨です。雨がとても強くて、外に出るのは難しいです。"
            "あおいとけんたは大学の図書館にいます。\n\n"
            "「雨が強いね。今日は外に出られないね」とあおいが言いました。\n\n"
            "「そうだね。でも、図書館でいろいろなことができるよ」"
            "とけんたが言いました。\n\n"
            "「そうだね。本が借りられるし、勉強もできる」\n\n"
            "「図書館のコンピューターも使えるよ。レポートが書けるね」"
            "とけんたが言いました。\n\n"
            "「じゃあ、今日はここで勉強しましょう。あの席に座れる？」"
            "とあおいが聞きました。\n\n"
            "「大丈夫。座れるよ」\n\n"
            "二人は席に座って、勉強を始めました。あおいはレポートを書きました。"
            "けんたは本を読みました。\n\n"
            "一時間後、あおいはけんたに言いました。「少し休みたい。カフェに行けない？」\n\n"
            "「図書館の一階にカフェがあるよ。コーヒーが飲めるよ」"
            "とけんたが言いました。\n\n"
            "「本当に？知らなかった！行きましょう！」\n\n"
            "二人は一階のカフェに行きました。コーヒーとケーキを注文しました。\n\n"
            "「この図書館は本当にいいね。雨の日でも、ここに来ることができるし、"
            "いろいろできるね」とあおいが言いました。\n\n"
            "「そうだよ。DVDも借りられるよ。映画を見ることができるんだよ」"
            "とけんたが言いました。\n\n"
            "「えっ、本当に？映画が見られるの！知らなかった。"
            "今日の午後、映画を見ましょう！」\n\n"
            "「いいね。どんな映画が見たい？」とけんたが聞きました。\n\n"
            "「日本語の映画が見たい！字幕なしで見られるか試したいな」"
            "とあおいが言いました。\n\n"
            "「いいね。日本語なら、全部の言葉が聞き取れると思うよ」"
            "とけんたが言いました。\n\n"
            "「そうかな。全部わかるようにがんばります！雨の日も楽しく過ごせるね」"
            "とあおいが言いました。"
        ),
    },
]


def run_correction_loop(text: str, stage: int, chapter: int,
                        ledger, client, stage_config: dict,
                        max_attempts: int = 5) -> tuple[str, object]:
    """Run validate→correct loop. Returns (corrected_text, final_validation)."""
    for attempt in range(max_attempts):
        result = validate(text, stage, "prose", ledger, chapter=chapter)

        status = "PASS" if result.passed else ("HARD_FAIL" if result.hard_fail else "SOFT_FAIL")
        print(f"    Attempt {attempt + 1}: {status} "
              f"(vocab={result.vocab.violation_rate:.3f}, "
              f"comp={result.vocab.comprehension_estimate:.3f}, "
              f"grammar_v={len(result.grammar.violations)}, "
              f"complexity_v={len(result.complexity.violations)})")

        if result.vocab.violations:
            viols = [f"{v.surface}({v.lemma})" for v in result.vocab.violations[:5]]
            print(f"      Vocab: {', '.join(viols)}")
        if result.grammar.violations:
            viols = [f"{v.name}" for v in result.grammar.violations[:5]]
            print(f"      Grammar: {', '.join(viols)}")

        if result.passed:
            return text, result

        if result.hard_fail:
            # Build combined violation list for the correction prompt
            all_violations = list(result.vocab.violations)

            # Also add grammar violations as pseudo-vocab violations
            # so the correction prompt includes them
            if result.grammar.violations:
                grammar_note = "\n\nALSO FIX GRAMMAR: " + ", ".join(
                    f"'{v.name}' pattern at position {v.span}"
                    for v in result.grammar.violations[:5]
                ) + " — these grammar patterns are NOT allowed at this level."
                # Append note to the first violation's suggestion
                if all_violations:
                    all_violations[0].suggestion = (
                        (all_violations[0].suggestion or "") + grammar_note)

            text = correct_text(
                client, text, all_violations,
                "vocab", stage_config)
        elif result.soft_fail:
            text = correct_text(
                client, text, result.complexity.violations,
                "complexity", stage_config)

    return text, result


def main():
    stage = 2
    chapter = 1
    stage_config = load_stage_config(stage)
    client = ClaudeCodeClient()

    # Initialize ledger with Stage 1 active, Stage 2 zone
    ledger = VocabLedger()
    if not MASTER_VOCAB_PATH.exists():
        print(f"ERROR: {MASTER_VOCAB_PATH} not found.")
        sys.exit(1)
    master_vocab = json.loads(MASTER_VOCAB_PATH.read_text(encoding="utf-8"))
    for entry in master_vocab:
        if entry["stage"] == 1:
            ledger.words[entry["kanji"]] = {
                "count": 15, "status": "active",
                "stage_introduced": 1, "last_seen_episode": "seed",
            }
        elif entry["stage"] == 2:
            ledger.words[entry["kanji"]] = {
                "count": 5, "status": "zone",
                "stage_introduced": 2, "last_seen_episode": "seed",
            }
    ledger._rebuild_form_index()
    print(f"Ledger: {len(ledger.words)} words "
          f"({len(ledger.get_active_words())} active, "
          f"{len(ledger.get_zone_words())} zone)\n")

    print("=" * 60)
    print("STAGE 2 CH.1 — CONSTRAINT FIX LOOP")
    print("=" * 60)

    all_episodes = []
    pass_count = 0

    for ep_data in EPISODES:
        ep_id = ep_data["id"]
        print(f"\n── {ep_id}: {ep_data['title']} ──")
        print(f"  Original: {len(ep_data['text'])} chars")

        corrected, result = run_correction_loop(
            ep_data["text"], stage, chapter, ledger, client, stage_config)

        passed = result.passed
        if passed:
            pass_count += 1

        print(f"  Final: {'✓ PASS' if passed else '✗ FAIL'} "
              f"({len(corrected)} chars, "
              f"comp={result.vocab.comprehension_estimate:.1%})")

        # Annotate
        ann = annotate(corrected, stage, ledger,
                       stage_config.get("furigana_threshold", 6))
        curated = curate_notes(ann, stage)

        # Record in ledger
        lemmas = [t.lemma for t in ann.tokens]
        ledger.record_episode(lemmas, ep_id)

        meta = {
            "episode_id": ep_id,
            "stage": stage,
            "chapter": chapter,
            "arc": ep_data["arc"],
            "situation": ep_data["situation"],
            "generated_at": datetime.now().isoformat(),
            "content_type": "reader",
            "validation": {
                "vocab_violation_rate": result.vocab.violation_rate,
                "comprehension_estimate": result.vocab.comprehension_estimate,
                "grammar_violations": [v.name for v in result.grammar.violations],
            },
        }

        episode = ReaderEpisode(
            id=ep_id,
            outline={"title": ep_data["title"],
                     "characters_in_episode": ["あおい", "けんた"],
                     "setting": "", "emotional_tone": ""},
            raw=corrected, annotated=ann, meta=meta,
            curated_notes=curated,
        )
        all_episodes.append(episode)

    # Build EPUBs
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {pass_count}/{len(EPISODES)} passed")
    print("=" * 60)

    for ep in all_episodes:
        epub_bytes = build_epub([ep], stage)
        out_dir = OUTPUTS_DIR / f"stage{stage}" / "readers" / f"arc_{ep.meta['arc']}"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{ep.id}.epub"
        path.write_bytes(epub_bytes)
        print(f"  {path} ({len(epub_bytes):,} bytes)")

    combined = build_epub(all_episodes, stage, "道 — Stage 2 Ch.1 Readers")
    combined_path = OUTPUTS_DIR / f"stage{stage}" / "readers" / "stage2_ch1_readers.epub"
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined_path.write_bytes(combined)
    print(f"  Combined: {combined_path} ({len(combined):,} bytes)")

    print(f"\n=== Done ===")


if __name__ == "__main__":
    main()
