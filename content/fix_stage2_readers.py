"""Validate and constraint-fix 5 Stage 2 reader episodes (full stage grammar).

Usage (from content/):
    python3.11 fix_stage2_readers.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import OUTPUTS_DIR, MASTER_VOCAB_PATH
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
        "id": "s2_reader_ep001",
        "title": "本屋のアルバイト",
        "arc": "daily_life",
        "situation": "あおいは本屋でアルバイトを始めた",
        "text": "あおいは先週から大学の近くの本屋でアルバイトを始めた。小さい頃から本が大好きで、本屋で働くことが夢だったから、採用されてとても嬉しかった。しかし、最初の日はとても緊張した。レジの前に立つと手が少し震えた。\n\n「すみません、レジの使い方を教えてもらえますか？」とあおいは先輩のゆかさんに頼んだ。ゆかさんは丁寧に一つ一つ教えてくれた。「最初は難しく感じるけど、慣れればすぐにできますよ」とゆかさんが笑いながら言った。あおいは何度も練習して、三日目にはレジをうまく使えるようになった。お客さんから「ありがとう」と言われるたびに、少しずつ自信がついてきた。\n\n四日目は棚の整理を手伝った。高いところには手が届かなかったが、小さい台を使えばどこでも届くことができた。午後になって、一人のお客さんが「料理の本はどこにありますか？」と聞いてきた。あおいはドキドキしたが、「少し待ってください」と言って、パソコンで場所を調べた。そして「あちらの棚の二段目にあります」と案内することができた。お客さんは「ありがとう、助かりました」と笑顔で言ってくれた。その一言がとても嬉しかった。\n\nその夜、あおいはけんたにメッセージを送った。「今日、一人でお客さんを案内できたよ！最初は緊張したけど、ちゃんとできた」けんたからすぐに返事が来た。「よかった！あおいなら絶対できると思ってたよ」その言葉を読んで、あおいはまた明日も頑張ろうと思った。本が好きだから、この仕事は自分にぴったりだと感じた。",
    },
    {
        "id": "s2_reader_ep002",
        "title": "試験の結果",
        "arc": "school",
        "situation": "期末試験の結果発表の日",
        "text": "今日は後期の試験の結果が発表される日だった。あおいは朝からずっと心配していた。今回の試験はとても難しくて、答えを何問か書き間違えてしまったと思っていたからだ。試験が終わった後も、ずっと不安な気持ちが続いた。\n\n掲示板の前にはたくさんの学生が集まっていた。あおいも人ごみの中に入って、リストの中に自分の名前を探した。結果を見た瞬間、驚いた。なんと、七十九点だった。思っていたより全然良かった。しかし、隣に立っていたけんたの点数も目に入ってしまった。けんたは九十一点だった。\n\n「けんた、すごい点数だね。どうやって勉強したの？」とあおいは聞いた。「毎日少しずつやったよ。試験の三週間前から始めていたら、もっとよく準備できたと思う」とけんたが答えた。あおいは少し悔しかった。私も早く始めていたら、もっといい点が取れたのに、と思った。\n\n廊下で先生に会った時、「あおいさん、今回はよく頑張りましたよ」と声をかけられた。先生に褒められて、あおいは少し気持ちが楽になった。次の試験では、もっと早くから計画を立てて勉強を始めようと強く思った。",
    },
    {
        "id": "s2_reader_ep003",
        "title": "サプライズパーティー",
        "arc": "social",
        "situation": "けんたの誕生日のためにサプライズパーティーを計画する",
        "text": "けんたの誕生日まであと一週間しかなかった。あおいはけんたのために、サプライズパーティーを計画していた。本人には絶対に教えてはいけないから、連絡はみかとはるの二人だけにした。\n\nまず、あおいは友達のみかとはるを呼んで相談した。「けんたを驚かせるために、みんなで大学の近くのカフェを予約しよう」とあおいが提案すると、二人はすぐに賛成した。あおいはその日のうちにカフェに電話して、三人分の席を予約することができた。\n\n次に、プレゼントを考えた。けんたは音楽が大好きだから、みんなでお金を出し合って、新しいイヤホンを買ってあげようと決めた。あおいはイヤホンをきれいな紙で包んで、大きなリボンをかけた。「きっと喜んでくれるよ」とはるが言った。「そうだね、けんたはイヤホンが欲しいって前に言ってたし、いつも音楽を聴いてるし、絶対嬉しいと思う」とあおいが答えた。\n\n当日、あおいはけんたに「一緒にカフェに行こう」と誘った。カフェに入ると、みかとはるが「サプライズ！誕生日おめでとう！」と叫んだ。けんたはびっくりして目を大きく開けた。プレゼントを渡すと、けんたはとても喜んでくれた。「こんなにいいものをもらえると思わなかった。本当にありがとう」と言った。あおいはけんたの笑顔を見て、計画して良かったと心から思った。",
    },
    {
        "id": "s2_reader_ep004",
        "title": "夏祭りの夜",
        "arc": "seasonal",
        "situation": "七月の夏祭りにあおいとけんたが出かける",
        "text": "七月になって、町の夏祭りの日が近くなった。あおいはけんたと一緒に行く約束をしていた。\n\n祭りの前の日の夜、あおいはお母さんに浴衣を着せてもらった。「きれいね。よく似合うよ」とお母さんが笑顔で言ってくれた。あおいは嬉しかった。小さい頃は浴衣を自分で着られなかったが、毎年少しずつ練習して、今は帯以外は一人で着られるようになった。\n\n祭り会場に着くと、たくさんの屋台が並んでいた。たこ焼きや焼き鳥のいい匂いがして、人もたくさんいて、とても賑やかだった。「お腹が空いたし、暑いし、まずかき氷を食べよう」とけんたが言った。二人はかき氷を食べながら屋台を見て回った。\n\n「あ、金魚すくいだ！あおい、やろう」とけんたが言った。けんたはとても楽しそうだったし、上手そうだったので、あおいも挑戦した。しかし、あおいのポイはすぐに破れてしまった。けんたは三匹すくうことができた。「毎年やってれば、だんだんうまくできるようになるよ」とけんたが笑いながら言った。\n\n夜になって花火が始まった。大きくてきれいな花火が次々と夜空に上がった。あおいは「来年もけんたと一緒に来たい」とそっと思った。",
    },
    {
        "id": "s2_reader_ep005",
        "title": "なくした財布",
        "arc": "daily_life",
        "situation": "大学で財布をなくしてけんたと探す",
        "text": "月曜日の朝、あおいは大学に着いてすぐ、財布がないことに気がついた。バッグの中を何度も探したが、どこにも見つからなかった。授業料が入っていたので、とても困った。\n\n「けんた、財布をなくして困ってる。少しお金を貸してくれる？」とあおいはけんたに電話した。けんたはすぐに「いいよ、今から行く」と言ってくれた。あおいはほっとした。けんたが来てくれれば、今日の食事の心配はしなくてよかった。\n\n昼休みに、二人で財布を探した。「昨日どこに行ったか思い出してみて。そうすれば、もっと早く見つかると思うよ」とけんたが言った。あおいはよく考えた。昨日は午後に図書館で勉強して、夕方コンビニに寄って飲み物を買った。「コンビニに財布を置いてきたと思う」とあおいが言った。\n\n二人でコンビニに行くと、店員さんが「お客様、もしかしてこちらですか？」と財布を出してくれた。あおいは「よかった！」と大きな声で言った。財布はカウンターの下に落ちていたそうだ。「ちゃんと確認すればよかったのに、急いでいたから気がつかなかった」とあおいが言うと、けんたは「見つかったんだから、いいよ」と笑った。あおいはけんたに心から感謝した。",
    },
]


def run_correction_loop(text, stage, ledger, client, stage_config, max_attempts=5):
    """Validate→correct loop. Returns (corrected_text, final_result)."""
    for attempt in range(max_attempts):
        result = validate(text, stage, "prose", ledger)
        status = "PASS" if result.passed else ("HARD" if result.hard_fail else "SOFT")
        vr = result.vocab.violation_rate
        comp = result.vocab.comprehension_estimate
        gv = len(result.grammar.violations)
        cv = len(result.complexity.violations)
        print(f"    [{attempt+1}] {status} vocab={vr:.3f} comp={comp:.3f} gram={gv} cmplx={cv}")

        if result.vocab.violations:
            vs = [f"{v.surface}" for v in result.vocab.violations[:6]]
            print(f"        vocab: {', '.join(vs)}")
        if result.grammar.violations:
            gs = [v.name for v in result.grammar.violations[:4]]
            print(f"        grammar: {', '.join(gs)}")

        if result.passed:
            return text, result

        if result.hard_fail:
            all_viols = list(result.vocab.violations)
            if result.grammar.violations:
                grammar_note = (" ALSO: these grammar patterns are NOT allowed"
                                " at this level and must be rewritten: " +
                                ", ".join(f"'{v.name}'" for v in result.grammar.violations[:5]) +
                                ". Do NOT use かもしれない, ようだ, みたいだ, or other Stage 3+ grammar.")
                if all_viols:
                    all_viols[0].suggestion = (all_viols[0].suggestion or "") + grammar_note
                else:
                    # Grammar-only violations: create a dummy violation
                    from rule_engine.vocab_checker import VocabViolation
                    all_viols.append(VocabViolation(
                        surface="[grammar]", lemma="[grammar]",
                        position=0, stage_required=None, current_stage=stage,
                        suggestion=grammar_note))
            text = correct_text(client, text, all_viols, "vocab", stage_config)
        elif result.soft_fail:
            text = correct_text(client, text, result.complexity.violations,
                                "complexity", stage_config)

        # If we're stuck on the same issue for 3+ attempts, try regenerating
        # the problematic section via claude -p directly
        if attempt >= 3 and not result.passed:
            from generator.claude_backend import ClaudeCodeClient
            import subprocess
            issues = []
            for v in result.vocab.violations[:3]:
                issues.append(f"word '{v.surface}' is not allowed")
            for v in result.grammar.violations[:3]:
                issues.append(f"grammar '{v.name}' is not allowed")
            for v in result.complexity.violations[:3]:
                issues.append(f"{v.issue}")
            issue_str = "; ".join(issues)
            prompt = (f"Rewrite this Japanese graded reader text to fix these issues: {issue_str}.\n"
                      f"Keep the story the same but use simpler vocabulary and shorter sentences.\n"
                      f"Do NOT use: かもしれない, ようだ, みたいだ, 祭り.\n"
                      f"Output ONLY the corrected Japanese text.\n\n{text}")
            try:
                res = subprocess.run(
                    ["claude", "-p", "--output-format", "text", "--allowedTools", "",
                     "--model", "haiku", prompt],
                    capture_output=True, text=True, timeout=120)
                if res.returncode == 0 and len(res.stdout.strip()) > 100:
                    text = res.stdout.strip()
            except Exception:
                pass
    return text, result


def main():
    stage = 2
    stage_config = load_stage_config(stage)
    client = ClaudeCodeClient()

    ledger = VocabLedger()
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
    print(f"Ledger: {len(ledger.words)} words\n")

    print("=" * 60)
    print("STAGE 2 READERS — CONSTRAINT FIX LOOP")
    print("=" * 60)

    all_episodes = []
    pass_count = 0

    for ep_data in EPISODES:
        ep_id = ep_data["id"]
        print(f"\n── {ep_id}: {ep_data['title']} ({len(ep_data['text'])} chars) ──")

        corrected, result = run_correction_loop(
            ep_data["text"], stage, ledger, client, stage_config)

        passed = result.passed
        if passed:
            pass_count += 1
        print(f"  → {'✓ PASS' if passed else '✗ FAIL'} "
              f"({len(corrected)} chars, comp={result.vocab.comprehension_estimate:.1%})")

        ann = annotate(corrected, stage, ledger,
                       stage_config.get("furigana_threshold", 6))
        curated = curate_notes(ann, stage)
        lemmas = [t.lemma for t in ann.tokens]
        ledger.record_episode(lemmas, ep_id)

        meta = {
            "episode_id": ep_id, "stage": stage, "arc": ep_data["arc"],
            "situation": ep_data["situation"],
            "generated_at": datetime.now().isoformat(),
            "content_type": "reader",
            "validation": {
                "vocab_violation_rate": result.vocab.violation_rate,
                "comprehension_estimate": result.vocab.comprehension_estimate,
            },
        }
        episode = ReaderEpisode(
            id=ep_id,
            outline={"title": ep_data["title"],
                     "characters_in_episode": ["あおい", "けんた"],
                     "setting": "", "emotional_tone": ""},
            raw=corrected, annotated=ann, meta=meta, curated_notes=curated,
        )
        all_episodes.append(episode)

    # Also save intermediate JSON for each episode
    json_dir = OUTPUTS_DIR / f"stage{stage}" / "readers" / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    for ep in all_episodes:
        ep_json = {
            "id": ep.id,
            "title": ep.outline["title"],
            "raw_text": ep.raw,
            "meta": ep.meta,
            "tokens": [
                {"surface": t.surface, "lemma": t.lemma, "furigana": t.furigana,
                 "gloss": {"en": t.gloss.en, "pos": t.gloss.pos} if t.gloss else None,
                 "status": t.status}
                for t in ep.annotated.tokens
            ],
            "curated_notes": {
                "vocab": [{"surface": v.surface, "reading": v.reading,
                           "gloss_en": v.gloss_en} for v in ep.curated_notes.vocab],
                "grammar": [{"display": g.display, "explanation": g.explanation}
                            for g in ep.curated_notes.grammar],
            } if ep.curated_notes else None,
        }
        jp = json_dir / f"{ep.id}.json"
        jp.write_text(json.dumps(ep_json, ensure_ascii=False, indent=2), encoding="utf-8")

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

    combined = build_epub(all_episodes, stage, "道 — Stage 2 Readers")
    combined_path = OUTPUTS_DIR / f"stage{stage}" / "readers" / "stage2_readers.epub"
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined_path.write_bytes(combined)
    print(f"  Combined: {combined_path} ({len(combined):,} bytes)")

    print(f"\n  JSON intermediates: {json_dir}/")
    print(f"\n=== Done ===")


if __name__ == "__main__":
    main()
