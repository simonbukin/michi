"""Generate 5 Stage 2 Chapter 1 reader episodes.

Corrected acquisition math:
  - new_words_per_episode: 3
  - target_text_chars: 800
  - Grammar ceiling: all Stage 1 + potential form (Stage 2 Ch.1)
  - Comprehension target: 98%

Usage (from content/):
    python3.11 generate_stage2_ch1_readers.py
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


STAGE2_CH1_EPISODES = [
    {
        "id": "s2_ch01_daily_life_ep001",
        "arc": "daily_life",
        "situation": "新しい料理に挑戦する",
        "outline": {
            "title": "お弁当を作れるかな",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "あおいのアパートの台所",
            "emotional_tone": "挑戦",
        },
        "text": (
            "あおいは毎日コンビニでお昼ごはんを買っています。\n\n"
            "でも、最近お金があまりありません。「自分でお弁当を作れたら、お金が節約できる」と思いました。\n\n"
            "日曜日の朝、あおいはスーパーに行きました。卵とお米と野菜を買いました。全部で五百円でした。コンビニのお弁当より安いです。\n\n"
            "家に帰って、まずお米を炊きます。お米は洗って、水を入れて、炊飯器のボタンを押します。これは簡単です。\n\n"
            "次に卵焼きを作ります。卵を三つ割って、少し砂糖を入れて、混ぜます。フライパンに油を入れて、焼きます。\n\n"
            "でも、うまく巻けません。「あれ？お母さんはいつも上手に巻ける のに」\n\n"
            "三回目に、やっと丸い形にできました。少し焦げたけど、味は大丈夫です。\n\n"
            "お弁当箱にごはんを入れて、卵焼きを入れて、野菜も少し入れました。きれいなお弁当ができました。\n\n"
            "写真を撮って、けんたに送りました。\n\n"
            "「すごい！自分で作れたの？」とけんたが返事をくれました。\n\n"
            "「うん。毎日は作れないかもしれないけど、週に三回は作りたい」\n\n"
            "「僕も作れるようになりたいな。今度教えて」\n\n"
            "月曜日、あおいは自分のお弁当を持って学校に行きました。友達が「おいしそう」と言ってくれました。少し嬉しかったです。"
        ),
    },
    {
        "id": "s2_ch01_daily_life_ep002",
        "arc": "daily_life",
        "situation": "自転車に乗れるようになりたい",
        "outline": {
            "title": "自転車の練習",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "大きい公園",
            "emotional_tone": "努力と達成",
        },
        "text": (
            "あおいは自転車に乗れません。小さい時に練習したことがありますが、すぐに怖くなって、やめてしまいました。\n\n"
            "でも、大学の近くに自転車で行ける店がたくさんあります。歩くと三十分かかりますが、自転車なら十分で行けます。\n\n"
            "「自転車に乗れたら便利だな」とあおいは思いました。\n\n"
            "土曜日、けんたに電話しました。「自転車の練習を手伝ってくれない？」\n\n"
            "けんたは「いいよ」と言ってくれました。けんたは小さい時から自転車に乗れます。\n\n"
            "二人は大きい公園に行きました。けんたが友達から自転車を借りてきてくれました。\n\n"
            "「まず、座って、足を地面につけて。そして、ゆっくりペダルを踏んでみて」\n\n"
            "あおいはペダルを踏みました。でも、すぐにバランスが取れなくなって、止まりました。\n\n"
            "「大丈夫。僕が後ろを持っているから」\n\n"
            "けんたが自転車の後ろを持って、あおいはもう一度ペダルを踏みました。今度は少し進めました。\n\n"
            "何回も練習しました。一時間後、あおいは一人で二十メートルぐらい走れるようになりました。\n\n"
            "「できた！少しだけど、一人で乗れた！」\n\n"
            "「すごいよ。来週も練習すれば、もっと上手に乗れるようになるよ」\n\n"
            "あおいは嬉しくて、「来週もお願いね」と言いました。体は疲れたけど、とても楽しい一日でした。"
        ),
    },
    {
        "id": "s2_ch01_school_ep001",
        "arc": "school",
        "situation": "英語の発表ができるか心配している",
        "outline": {
            "title": "英語の発表",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "大学の教室と廊下",
            "emotional_tone": "不安から自信へ",
        },
        "text": (
            "来週の火曜日、英語の授業で発表があります。五分間、英語で話さなければなりません。\n\n"
            "あおいは英語が得意ではありません。読むことはできますが、話すのは難しいです。\n\n"
            "「五分も英語で話せるかな」と心配しています。\n\n"
            "テーマは自由です。あおいは日本の食べ物について話すことにしました。食べ物の話なら、知っている言葉が多いからです。\n\n"
            "家に帰って、原稿を書きました。「日本にはたくさんのおいしい食べ物があります。寿司、天ぷら、ラーメン……」\n\n"
            "書くことはできました。でも、声に出して読むと、発音が難しい言葉がいくつかあります。\n\n"
            "次の日、けんたに会いました。\n\n"
            "「英語の発表、大丈夫？」とけんたが聞きました。\n\n"
            "「うーん、自信がない。英語で上手に話せないと思う」\n\n"
            "「じゃあ、僕の前で練習してみて。聞いてあげるから」\n\n"
            "あおいは廊下のベンチで、けんたの前で発表の練習をしました。\n\n"
            "最初は声が小さかったけど、だんだん大きく話せるようになりました。\n\n"
            "「いいよ。わかりやすいし、面白い」とけんたが言いました。\n\n"
            "「本当？もっと練習すれば、きっと大丈夫だよね」\n\n"
            "火曜日、あおいは発表しました。少し間違えたけど、最後まで話せました。\n\n"
            "先生が「よくできました」と言ってくれました。あおいは「練習してよかった」と思いました。"
        ),
    },
    {
        "id": "s2_ch01_daily_life_ep003",
        "arc": "daily_life",
        "situation": "友達と電話で話す",
        "outline": {
            "title": "遠くの友達",
            "characters_in_episode": ["あおい"],
            "setting": "あおいの部屋",
            "emotional_tone": "懐かしさと温かさ",
        },
        "text": (
            "あおいには高校の時の友達がいます。名前はみさきです。みさきは今、北海道の大学に通っています。\n\n"
            "二人は毎月一回、電話で話します。今日がその日です。\n\n"
            "夜の八時に電話がきました。\n\n"
            "「あおい、元気？」\n\n"
            "「元気だよ。みさきは？北海道はもう寒い？」\n\n"
            "「すごく寒い。もうコートがないと外に出られないよ。東京はまだ暖かいでしょう？」\n\n"
            "「うん、まだ暖かいけど、朝は少し寒くなってきた」\n\n"
            "みさきは大学で英語を勉強しています。「最近、英語の本が少し読めるようになったの」と嬉しそうに言いました。\n\n"
            "「すごいね。私は英語が全然だめ」とあおいは笑いました。\n\n"
            "「あおいは日本語の作文が上手だったじゃん。私は日本語の作文が書けなくて、いつもあおいに見せてもらっていたよ」\n\n"
            "「そうだったね」あおいは高校の時のことを思い出しました。\n\n"
            "二人はたくさん話しました。大学の授業のこと、新しい友達のこと、おいしかった食べ物のこと。\n\n"
            "「冬休みに東京に帰れたら、一緒にごはんを食べよう」とみさきが言いました。\n\n"
            "「うん、絶対。楽しみにしているよ」\n\n"
            "電話を切った後、あおいは少し寂しくなりました。でも、友達がいることは嬉しいことだと思いました。\n\n"
            "遠くにいても、電話で話せば、近くにいるみたいです。"
        ),
    },
    {
        "id": "s2_ch01_seasonal_ep001",
        "arc": "seasonal",
        "situation": "秋の休日に出かける",
        "outline": {
            "title": "秋の一日",
            "characters_in_episode": ["あおい", "けんた"],
            "setting": "公園と商店街",
            "emotional_tone": "穏やかな楽しさ",
        },
        "text": (
            "十一月になりました。木の葉が赤や黄色に変わっています。\n\n"
            "日曜日の朝、けんたから連絡がきました。「今日は天気がいいから、どこかに行かない？」\n\n"
            "あおいは「いいね。公園に行こう。紅葉が見られるかもしれない」と返事をしました。\n\n"
            "二人は電車で大きい公園に行きました。\n\n"
            "公園に着くと、たくさんの人がいました。みんな紅葉を見に来ています。\n\n"
            "赤い木と黄色い木がとてもきれいです。あおいは写真をたくさん撮りました。\n\n"
            "「ここから富士山が見えるらしいよ」とけんたが地図を見ながら言いました。\n\n"
            "小さい丘に登りました。でも、今日は雲が多くて、富士山は見えませんでした。\n\n"
            "「残念。でも、天気がいい日に来れば、きっと見えるよ」\n\n"
            "「じゃあ、冬に来よう。冬の方がよく見えるって聞いたことがある」\n\n"
            "公園を歩いた後、近くの商店街に行きました。\n\n"
            "小さい和菓子の店がありました。「あ、焼き芋が買える」とあおいが言いました。\n\n"
            "二人は焼き芋を一つずつ買いました。温かくて、甘くて、秋の味がします。\n\n"
            "「秋は好きだな。食べ物がおいしい季節だよね」とけんたが言いました。\n\n"
            "「うん。でも、すぐ冬になるから、今のうちにたくさん紅葉を見ておきたい」\n\n"
            "帰りの電車の中で、あおいは今日撮った写真を見ました。きれいな写真がたくさん撮れました。\n\n"
            "「今日は楽しかった。ありがとう」\n\n"
            "「うん。また来月も出かけよう」"
        ),
    },
]


def main():
    stage = 2
    chapter = 1
    stage_config = load_stage_config(stage)

    # Initialize ledger: Stage 1 words as "active", Stage 2 as "zone"
    ledger = VocabLedger()
    if not MASTER_VOCAB_PATH.exists():
        print(f"ERROR: {MASTER_VOCAB_PATH} not found.")
        print("Run: cd shared/vocab && python3.11 build_master_vocab.py")
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
    print("STAGE 2 CHAPTER 1 READERS (corrected math)")
    print(f"  Target: 800 chars, 3 new words/ep, potential form grammar")
    print("=" * 60)

    all_episodes = []

    for ep_data in STAGE2_CH1_EPISODES:
        ep_id = ep_data["id"]
        text = ep_data["text"]
        print(f"\n── {ep_id}: {ep_data['outline']['title']} ──")
        print(f"  Text length: {len(text)} chars")

        # Validate with chapter-level grammar gating
        result = validate(text, stage, "prose", ledger, chapter=chapter)

        # Comprehension model
        content_tokens = int(len(text) * 0.25)
        print(f"  Content tokens (est): {content_tokens}")
        print(f"  Validation: passed={result.passed}, "
              f"vocab_rate={result.vocab.violation_rate:.3f}, "
              f"comprehension={result.vocab.comprehension_estimate:.3f}")

        if result.vocab.violations:
            print(f"  Vocab violations ({len(result.vocab.violations)}):")
            for v in result.vocab.violations[:10]:
                print(f"    {v.surface} ({v.lemma})")

        if result.grammar.violations:
            print(f"  Grammar violations ({len(result.grammar.violations)}):")
            for v in result.grammar.violations[:5]:
                print(f"    {v.display} ({v.name}, stage {v.stage})")

        if not result.passed:
            if result.hard_fail:
                print(f"  ⚠ HARD FAIL — would need correction in production")
            elif result.soft_fail:
                print(f"  ⚠ SOFT FAIL (complexity) — would need simplification")

        # Annotate
        ann = annotate(text, stage, ledger, stage_config.get("furigana_threshold", 6))
        glossed = [t for t in ann.tokens if t.gloss]
        print(f"  Annotation: {len(ann.tokens)} tokens, {len(glossed)} glossed")

        # Curate notes
        curated = curate_notes(ann, stage)
        print(f"  Notes: {len(curated.vocab)} vocab, {len(curated.grammar)} grammar")

        # Grammar patterns found
        if ann.grammar_patterns:
            seen = set()
            for pat in ann.grammar_patterns:
                if pat.name not in seen:
                    seen.add(pat.name)
            print(f"  Grammar patterns: {', '.join(sorted(seen))}")

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
            id=ep_id, outline=ep_data["outline"],
            raw=text, annotated=ann, meta=meta,
            curated_notes=curated,
        )
        all_episodes.append(episode)

    # Write EPUBs
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

    # Combined EPUB
    combined = build_epub(all_episodes, stage, "道 — Stage 2 Ch.1 Readers")
    combined_path = OUTPUTS_DIR / f"stage{stage}" / "readers" / "stage2_ch1_readers.epub"
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined_path.write_bytes(combined)
    print(f"  Combined: {combined_path} ({len(combined):,} bytes)")

    print(f"\nLedger after: {len(ledger.words)} words tracked")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
