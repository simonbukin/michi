"""Standalone frequency audit tool for master_vocab.json stage assignments.

Shows exactly what's in each stage's vocab pool — frequency distribution,
coverage gaps, and pedagogical issues. Run standalone:

    cd shared/vocab && python3.11 audit_stages.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASTER_VOCAB = HERE / "master_vocab.json"

# Expected new words per stage (cumulative targets minus previous)
STAGE_NEW_WORDS = {1: 800, 2: 700, 3: 1500, 4: 2000, 5: 3000, 6: 2000}

# Frequency bands
FREQ_BANDS = {
    1: (1, 1500),
    2: (1501, 3500),
    3: (3501, 7000),
    4: (7001, 14000),
    5: (14001, 25000),
    6: (25001, None),
}

# Comprehension model parameters
CONTENT_TOKENS_PER_CHAR = 0.25
AVG_NEW_WORD_OCCURRENCES = 1.3

STAGE_PARAMS = {
    1: {"new_per_ep": 2, "chars": 600, "target_comp": 0.98},
    2: {"new_per_ep": 3, "chars": 800, "target_comp": 0.98},
    3: {"new_per_ep": 5, "chars": 1000, "target_comp": 0.97},
    4: {"new_per_ep": 7, "chars": 1200, "target_comp": 0.96},
    5: {"new_per_ep": 8, "chars": 1600, "target_comp": 0.95},
    6: {"new_per_ep": 8, "chars": 2000, "target_comp": 0.95},
}


def main():
    if not MASTER_VOCAB.exists():
        print(f"ERROR: {MASTER_VOCAB} not found. Run build_master_vocab.py first.")
        return

    entries = json.loads(MASTER_VOCAB.read_text(encoding="utf-8"))

    # Group by stage
    by_stage: dict[int, list[dict]] = {s: [] for s in range(1, 7)}
    for e in entries:
        s = e.get("stage")
        if s and s in by_stage:
            by_stage[s].append(e)

    print("=" * 70)
    print("STAGE FREQUENCY AUDIT")
    print("=" * 70)

    for stage in range(1, 7):
        words = by_stage[stage]
        lo, hi = FREQ_BANDS[stage]
        params = STAGE_PARAMS[stage]

        with_freq = [w for w in words if w.get("freq_rank")]
        without_freq = [w for w in words if not w.get("freq_rank")]
        with_textbook = [w for w in words if w.get("textbook")]

        # Frequency stats
        ranks = sorted([w["freq_rank"] for w in with_freq])
        in_band = [r for r in ranks if r >= lo and (hi is None or r <= hi)]
        out_of_band = [r for r in ranks if r < lo or (hi is not None and r > hi)]

        # Comprehension estimate
        ct = int(params["chars"] * CONTENT_TOKENS_PER_CHAR)
        nw = params["new_per_ep"]
        comp = 1.0 - (nw * AVG_NEW_WORD_OCCURRENCES / ct)
        target = params["target_comp"]
        ok = "✓" if comp >= target else "✗"
        episodes = STAGE_NEW_WORDS[stage] // nw if nw > 0 else 0
        total_chars = episodes * params["chars"]

        print(f"\nStage {stage} ({len(words)} words, JPDB ranks {lo}-{hi or '∞'}):")
        print(f"  Expected new words: {STAGE_NEW_WORDS[stage]}")
        print(f"  Words with JPDB rank: {len(with_freq)}/{len(words)}")
        print(f"  Words without JPDB rank: {len(without_freq)}")
        print(f"  Words from textbook: {len(with_textbook)}")
        print(f"  In frequency band: {len(in_band)}, out of band: {len(out_of_band)}")

        if ranks:
            print(f"  Freq range: {min(ranks)}-{max(ranks)} "
                  f"(median: {ranks[len(ranks)//2]})")

        print(f"\n  Comprehension model:")
        print(f"    {nw} new/ep × {params['chars']}c → {ct} content tokens → {comp:.1%} {ok}")
        print(f"    Episodes needed: {episodes}")
        print(f"    Total chars: {total_chars:,}")

        # Top 20 by frequency
        top20 = sorted(with_freq, key=lambda w: w["freq_rank"])[:20]
        print(f"\n  Top 20 by frequency:")
        for w in top20:
            tb = " [textbook]" if w.get("textbook") else ""
            print(f"    {w['freq_rank']:>6}  {w['kanji']:<10} {w.get('english', '')[:40]}{tb}")

        # Bottom 20 by frequency
        bottom20 = sorted(with_freq, key=lambda w: w["freq_rank"])[-20:]
        print(f"\n  Bottom 20 by frequency:")
        for w in bottom20:
            tb = " [textbook]" if w.get("textbook") else ""
            print(f"    {w['freq_rank']:>6}  {w['kanji']:<10} {w.get('english', '')[:40]}{tb}")

        # Words without frequency data
        if without_freq:
            print(f"\n  Words without JPDB rank ({len(without_freq)}):")
            for w in without_freq[:15]:
                src = w.get("source", "?")
                print(f"    {w['kanji']:<10} src={src} {w.get('english', '')[:40]}")
            if len(without_freq) > 15:
                print(f"    ... and {len(without_freq) - 15} more")

    # Overall comprehension summary
    print("\n" + "=" * 70)
    print("COMPREHENSION SUMMARY")
    print("=" * 70)
    for stage in range(1, 7):
        params = STAGE_PARAMS[stage]
        ct = int(params["chars"] * CONTENT_TOKENS_PER_CHAR)
        nw = params["new_per_ep"]
        comp = 1.0 - (nw * AVG_NEW_WORD_OCCURRENCES / ct)
        target = params["target_comp"]
        ok = "✓" if comp >= target else "✗"
        episodes = STAGE_NEW_WORDS[stage] // nw if nw > 0 else 0
        total_chars = episodes * params["chars"]
        print(f"  Stage {stage}: {nw} new, {params['chars']}c → "
              f"{comp:.1%} (target {target:.0%}) {ok} | "
              f"{episodes} eps, {total_chars:,} chars")


if __name__ == "__main__":
    main()
