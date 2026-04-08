"""Generate 5 Stage 2 sample reader episodes for auditing.

Stage 2 parameters:
  - vocab_target: 1500 (Stage 1 base + 700 new)
  - new_words_per_episode: 6
  - target_text_chars: 600
  - target_comprehension: 0.98
  - Grammar unlocks: potential, passive, conditional (ba/tara), volitional,
    te_shimau, te_ageru/morau/kureru, you_ni_naru/suru, rashii, sou_da, noni, node, tame_ni

Usage (from content/):
    python3.11 generate_stage2_samples.py
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


STAGE2_READER_EPISODES = [
    {
        "id": "s2_daily_life_ep001",
        "arc": "daily_life",
        "situation": "初めて自分で料理を作ろうとしている",
        "outline": {
            "title": "初めてのカレー",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "あおいのアパート",
            "emotional_tone": "挑戦",
        },
        "text": (
            "あおいは今日、初めてカレーを作ることにしました。\n\n"
            "スーパーで野菜と肉を買いました。"
            "にんじん、じゃがいも、たまねぎ。全部で八百円でした。\n\n"
            "家に帰って、まず野菜を切ります。"
            "でも、たまねぎを切ったら、涙が出てしまいました。"
            "「痛い！目が痛い！」\n\n"
            "けんたに電話しました。\n\n"
            "「たまねぎが切れないんだけど……」\n\n"
            "「水の中で切ればいいよ」とけんたが教えてくれました。\n\n"
            "あおいはやってみました。本当だ。もう涙が出ません。\n\n"
            "肉を焼いて、野菜を入れて、水を入れました。"
            "三十分待ちます。\n\n"
            "カレーのいい匂いがします。\n\n"
            "「できた！」\n\n"
            "食べてみたら、少し辛かったけど、おいしかったです。"
            "写真を撮って、けんたに送りました。\n\n"
            "「おいしそう！今度食べさせて」とけんたが言いました。"
        ),
    },
    {
        "id": "s2_school_ep001",
        "arc": "school",
        "situation": "大学のテストの結果が返ってきた",
        "outline": {
            "title": "テストの結果",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "大学の教室",
            "emotional_tone": "不安から安心へ",
        },
        "text": (
            "今日、数学のテストが返されました。\n\n"
            "あおいは紙を見るのが怖いです。"
            "先週のテストは難しかったから、自信がありません。\n\n"
            "ゆっくり紙を開けました。\n\n"
            "八十五点。思ったより良かったです。\n\n"
            "「けんた、何点だった？」\n\n"
            "けんたは困った顔をしています。\n\n"
            "「六十点……。全然勉強しなかったからだ」\n\n"
            "「次のテストは一緒に勉強しよう」とあおいが言いました。\n\n"
            "けんたは「本当に？助かる」と嬉しそうに言いました。\n\n"
            "放課後、二人は図書館に行きました。"
            "あおいはけんたに問題の解き方を教えてあげました。\n\n"
            "「ああ、そうやればできるのか」とけんたが言います。\n\n"
            "「毎日少しずつやれば、きっと点数が上がるよ」\n\n"
            "けんたは頷きました。"
            "「次は絶対に頑張る」\n\n"
            "図書館を出たら、もう暗くなっていました。"
        ),
    },
    {
        "id": "s2_seasonal_ep001",
        "arc": "seasonal",
        "situation": "梅雨の季節に傘を忘れて困っている",
        "outline": {
            "title": "突然の雨",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "大学の出口",
            "emotional_tone": "困惑からほっこり",
        },
        "text": (
            "六月になりました。毎日雨が降っています。梅雨です。\n\n"
            "今日も朝は曇っていたのに、あおいは傘を持ってきませんでした。\n\n"
            "授業が終わって、外を見ると、強い雨が降っています。\n\n"
            "「どうしよう」\n\n"
            "走って帰ったら、濡れてしまいます。"
            "でもバスに乗れば、家の近くまで行けます。\n\n"
            "財布を見ました。二百円しかありません。バスは二百五十円です。\n\n"
            "「あおい！」\n\n"
            "けんたが大きい傘を持って走ってきました。\n\n"
            "「天気予報を見たから、二本持ってきたんだ」\n\n"
            "けんたは一本をあおいに渡してくれました。\n\n"
            "「ありがとう！本当に助かった」\n\n"
            "二人は傘をさして歩きます。"
            "雨の音が静かに聞こえます。\n\n"
            "「梅雨は嫌だけど、雨の音は好きだな」とあおいが言いました。\n\n"
            "「わかる。少し落ち着くよね」\n\n"
            "駅まで話しながら歩きました。"
        ),
    },
    {
        "id": "s2_social_ep001",
        "arc": "social",
        "situation": "アルバイトの面接に行く",
        "outline": {
            "title": "カフェの面接",
            "characters_in_episode": ["あおい"],
            "setting": "駅前のカフェ",
            "emotional_tone": "緊張と期待",
        },
        "text": (
            "あおいはアルバイトを探しています。"
            "お金がもっと必要になったからです。\n\n"
            "駅前のカフェが人を募集していました。"
            "「ここなら学校から近いし、働けそうだ」と思いました。\n\n"
            "面接は土曜日の午後二時です。"
            "あおいは白いシャツを着て、カフェに行きました。\n\n"
            "店長は優しそうな女の人でした。\n\n"
            "「コーヒーを入れたことはありますか？」\n\n"
            "「家では毎日入れています」\n\n"
            "「お客さんと話すのは得意ですか？」\n\n"
            "あおいは少し考えました。得意ではないけど、嫌いではありません。\n\n"
            "「頑張れると思います」\n\n"
            "店長は笑って、「来週の月曜日から来られますか？」と聞きました。\n\n"
            "あおいは驚きました。もう決まったのですか。\n\n"
            "「はい！行けます！」\n\n"
            "帰り道、あおいはとても嬉しかったです。"
            "けんたにすぐメッセージを送りました。\n\n"
            "「受かった！来週からカフェで働くよ」\n\n"
            "「おめでとう！コーヒー作ってね」"
        ),
    },
    {
        "id": "s2_exploration_ep001",
        "arc": "exploration",
        "situation": "週末に知らない町を歩いている",
        "outline": {
            "title": "迷子の散歩",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "知らない商店街",
            "emotional_tone": "好奇心と発見",
        },
        "text": (
            "日曜日、あおいとけんたは電車に乗りました。"
            "行ったことがない駅で降りてみました。\n\n"
            "小さい商店街がありました。"
            "古い店がたくさん並んでいます。\n\n"
            "「いい匂いがするね」とけんたが言いました。\n\n"
            "パン屋さんから焼きたてのパンの匂いがします。"
            "二人は中に入りました。\n\n"
            "「このメロンパン、おいしそう」\n\n"
            "一つずつ買って、外のベンチで食べました。"
            "やっぱりおいしかったです。\n\n"
            "もっと歩くと、古本屋が見えました。"
            "あおいは本が好きなので、入ってみたいと思いました。\n\n"
            "中はとても狭いけど、本がたくさんあります。"
            "あおいは古い地図の本を見つけました。百円です。\n\n"
            "「この町の昔の地図が載っている。面白い」\n\n"
            "けんたは隣の店で古いレコードを見ています。\n\n"
            "「知らない町を歩くのは楽しいね」とあおいが言いました。\n\n"
            "「また来よう。次はもっと遠くに行こう」\n\n"
            "夕方になって、二人は電車で帰りました。"
            "知らない町が、少しだけ好きな町になりました。"
        ),
    },
]


def main():
    stage = 2
    stage_config = load_stage_config(stage)

    # Initialize ledger: Stage 1 words as "active", Stage 2 as "zone"
    ledger = VocabLedger()
    if not MASTER_VOCAB_PATH.exists():
        print(f"ERROR: {MASTER_VOCAB_PATH} not found.")
        sys.exit(1)
    master_vocab = json.loads(MASTER_VOCAB_PATH.read_text(encoding="utf-8"))
    for entry in master_vocab:
        if entry["stage"] == 1:
            ledger.words[entry["kanji"]] = {
                "count": 15,
                "status": "active",
                "stage_introduced": 1,
                "last_seen_episode": "seed",
            }
        elif entry["stage"] == 2:
            ledger.words[entry["kanji"]] = {
                "count": 5,
                "status": "zone",
                "stage_introduced": 2,
                "last_seen_episode": "seed",
            }
    ledger._rebuild_form_index()
    print(f"Ledger: {len(ledger.words)} words "
          f"({len(ledger.get_active_words())} active, "
          f"{len(ledger.get_zone_words())} zone)\n")

    print("=" * 60)
    print("STAGE 2 SAMPLE READERS (for audit)")
    print("=" * 60)

    all_episodes = []

    for ep_data in STAGE2_READER_EPISODES:
        ep_id = ep_data["id"]
        text = ep_data["text"]
        print(f"\n── {ep_id}: {ep_data['outline']['title']} ──")
        print(f"  Text length: {len(text)} chars")

        # Validate
        result = validate(text, stage, "prose", ledger)
        print(f"  Validation: passed={result.passed}, "
              f"vocab_rate={result.vocab.violation_rate:.3f}, "
              f"comprehension={result.vocab.comprehension_estimate:.3f}")

        if result.vocab.violations:
            print(f"  Vocab violations ({len(result.vocab.violations)}):")
            for v in result.vocab.violations[:8]:
                print(f"    {v.surface} ({v.lemma})")

        if result.grammar.violations:
            print(f"  Grammar violations ({len(result.grammar.violations)}):")
            for v in result.grammar.violations[:5]:
                print(f"    {v.display} ({v.name}, stage {v.stage})")

        # Annotate
        ann = annotate(text, stage, ledger, stage_config.get("furigana_threshold", 6))
        glossed = [t for t in ann.tokens if t.gloss]
        print(f"  Annotation: {len(ann.tokens)} tokens, {len(glossed)} glossed")

        # Curate notes
        curated = curate_notes(ann, stage)
        print(f"  Notes: {len(curated.vocab)} vocab highlights, "
              f"{len(curated.grammar)} grammar highlights")
        for v in curated.vocab:
            r = f"（{v.reading}）" if v.reading else ""
            print(f"    {v.surface}{r} {v.gloss_en}")
        for g in curated.grammar:
            print(f"    {g.display} {g.explanation}")

        # Grammar patterns found
        if ann.grammar_patterns:
            seen = set()
            print(f"  Grammar patterns detected:")
            for pat in ann.grammar_patterns:
                if pat.name not in seen:
                    seen.add(pat.name)
                    print(f"    {pat.display} ({pat.name})")

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
    print("\n" + "=" * 60)
    print("EPUB OUTPUT")
    print("=" * 60)

    for ep in all_episodes:
        epub_bytes = build_epub([ep], stage)
        out_dir = OUTPUTS_DIR / f"stage{stage}" / "readers" / f"arc_{ep.meta['arc']}"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{ep.id}.epub"
        path.write_bytes(epub_bytes)
        print(f"  {path} ({len(epub_bytes):,} bytes)")

    # Combined EPUB for easy reading
    combined = build_epub(all_episodes, stage, "道 — Stage 2 Samples")
    combined_path = OUTPUTS_DIR / f"stage{stage}" / "readers" / "stage2_samples.epub"
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined_path.write_bytes(combined)
    print(f"  Combined: {combined_path} ({len(combined):,} bytes)")

    print(f"\nLedger after: {len(ledger.words)} words tracked")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
