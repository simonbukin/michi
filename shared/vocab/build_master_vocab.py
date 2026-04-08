"""Build master_vocab.json — the single source of truth for all vocabulary.

Stage assignment is frequency-driven:
  - JPDB media-frequency rank is the PRIMARY signal for stage placement
  - Tanos/Waller JLPT lists seed which words to include (there is no
    official JLPT word list — these are community approximations)
  - Textbook appendix entries can pull words to earlier stages
  - JMdict (via jamdict) provides all kanji/kana forms, POS, glosses

The pipeline:
  1. Collect candidate words from JLPT lists, textbook, and JPDB
  2. Enrich each with JMdict data (all forms, POS, glosses)
  3. Assign JPDB frequency rank to every entry
  4. Assign stage based on frequency rank (not JLPT level)
  5. Apply textbook overrides (textbook can pull words earlier)
  6. Gap-fill stages under target from JPDB-ranked JMdict entries

Output: master_vocab.json — flat JSON array sorted by (stage, freq_rank).

Usage:
    cd shared/vocab && python3.11 build_master_vocab.py
"""

import csv
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources"
REPO_ROOT = HERE.parent.parent
TEXTBOOK_DIR = REPO_ROOT / "textbook"
OUTPUT_PATH = HERE / "master_vocab.json"

JPDB_CSV = SOURCES / "jpdb_freq.csv"
OVERRIDES_JSON = SOURCES / "overrides.json"

# JLPT levels (used as seed lists, NOT for stage assignment)
JLPT_LEVELS = ["n5", "n4", "n3", "n2", "n1"]

# Stage targets for gap-filling
STAGE_TARGETS = {1: 800, 2: 1500, 3: 3000, 4: 5000, 5: 8000, 6: 10000}

# Header values to skip when parsing textbook vocab tables
HEADER_WORDS = {"Word", "Japanese", "単語", "Kanji"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _katakana_to_hiragana(text: str) -> str:
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return "".join(result)


def _hiragana_to_katakana(text: str) -> str:
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x3041 <= cp <= 0x3096:
            result.append(chr(cp + 0x60))
        else:
            result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# 1. Load JPDB frequency rankings
# ---------------------------------------------------------------------------


def load_jpdb() -> dict[tuple[str, str], int]:
    """Load JPDB CSV → dict of (term, reading) → freq_rank."""
    freq = {}
    with open(JPDB_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            term = row["term"].strip()
            reading = row["reading"].strip()
            rank = int(row["frequency"])
            key = (term, reading)
            if key not in freq:
                freq[key] = rank
    print(f"  JPDB: {len(freq):,} entries loaded")
    return freq


def jpdb_rank_for(jpdb: dict, term: str, reading: str) -> int | None:
    """Look up JPDB rank, trying multiple form combinations."""
    # Direct match
    if (term, reading) in jpdb:
        return jpdb[(term, reading)]
    # Try with hiragana reading
    hira = _katakana_to_hiragana(reading) if reading else ""
    if hira and (term, hira) in jpdb:
        return jpdb[(term, hira)]
    # Try term as both key parts (for kana-only words)
    if (term, term) in jpdb:
        return jpdb[(term, term)]
    if (term, "") in jpdb:
        return jpdb[(term, "")]
    # Try hiragana version of term
    hira_term = _katakana_to_hiragana(term)
    if hira_term != term:
        if (hira_term, hira_term) in jpdb:
            return jpdb[(hira_term, hira_term)]
        if (hira_term, "") in jpdb:
            return jpdb[(hira_term, "")]
    return None


# ---------------------------------------------------------------------------
# 2. Load JLPT (tanos/waller) lists
# ---------------------------------------------------------------------------


def load_jlpt() -> dict[int, dict]:
    """Load tanos CSVs → dict of jmdict_seq → {jlpt_level, kana, kanji, english}.

    These are community-sourced JLPT approximations. We use them to seed
    which words to include, but stage assignment comes from JPDB frequency.
    """
    entries: dict[int, dict] = {}
    for level_str in JLPT_LEVELS:
        path = SOURCES / f"tanos_{level_str}.tsv"
        if not path.exists():
            print(f"  WARNING: {path} not found, skipping")
            continue
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                seq_str = row["jmdict_seq"].strip()
                if not seq_str:
                    continue
                seq = int(seq_str)
                if seq in entries:
                    continue
                entries[seq] = {
                    "jmdict_seq": seq,
                    "kana": row["kana"].strip(),
                    "kanji": row.get("kanji", "").strip(),
                    "english": row.get("waller_definition", "").strip(),
                    "jlpt": level_str,
                    "source": f"tanos_{level_str}",
                }
                count += 1
            print(f"  JLPT {level_str.upper()}: {count} entries")
    print(f"  JLPT total: {len(entries)} unique seed words")
    return entries


# ---------------------------------------------------------------------------
# 3. Parse textbook appendices
# ---------------------------------------------------------------------------


def parse_textbook_vocab(stage_num: int) -> list[dict]:
    """Parse a textbook appendix_a_vocabulary.md into vocab entries."""
    filepath = TEXTBOOK_DIR / f"stage{stage_num}" / "appendix_a_vocabulary.md"
    if not filepath.exists():
        return []

    content = filepath.read_text(encoding="utf-8")
    entries = []
    in_supplementary = False

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("##") and any(
            kw in stripped.lower()
            for kw in ("supplementary", "particle", "function")
        ):
            in_supplementary = True
            continue

        if stripped.startswith("## ") and in_supplementary:
            if not any(
                kw in stripped.lower()
                for kw in ("supplementary", "particle", "function")
            ):
                in_supplementary = False

        if not stripped.startswith("|") or re.match(r"\|[\s-]+\|", stripped):
            continue

        parts = [p.strip() for p in stripped.split("|")]
        parts = [p for p in parts if p]

        if len(parts) < 3:
            continue
        if parts[0] in HEADER_WORDS:
            continue

        word = parts[0]
        reading = ""
        pitch = ""
        pos = ""
        english = ""
        chapter = ""

        if in_supplementary:
            pos = parts[1] if len(parts) >= 2 else ""
            english = parts[2] if len(parts) >= 3 else ""
        elif len(parts) >= 6:
            reading = parts[1].replace("—", "").replace("–", "").strip()
            pitch = parts[2].strip()
            pos = parts[3]
            english = parts[4]
            chapter = parts[5]
        elif len(parts) >= 4:
            reading = parts[1].replace("—", "").replace("–", "").strip()
            english = parts[3]
        elif len(parts) >= 3:
            english = parts[2]

        # Extract chapter number
        ch_num = None
        if chapter:
            m = re.search(r"(\d+)", chapter)
            if m:
                ch_num = int(m.group(1))

        entries.append(
            {
                "word": word,
                "reading": reading,
                "pitch": pitch,
                "pos": pos,
                "english": english,
                "chapter": ch_num,
                "stage": stage_num,
            }
        )

    return entries


def load_textbook() -> list[dict]:
    """Load all textbook appendix vocab across all stages."""
    all_entries = []
    for stage_num in range(1, 7):
        entries = parse_textbook_vocab(stage_num)
        if entries:
            print(f"  Textbook stage {stage_num}: {len(entries)} entries")
            all_entries.extend(entries)
    print(f"  Textbook total: {len(all_entries)} entries")
    return all_entries


# ---------------------------------------------------------------------------
# 4. JMdict enrichment via jamdict
# ---------------------------------------------------------------------------


def enrich_with_jamdict(
    jlpt_entries: dict[int, dict],
    textbook_entries: list[dict],
) -> dict[int, dict]:
    """Look up each entry in JMdict to get all forms, POS, glosses, and ID.

    Returns dict of jmdict_seq → enriched entry.
    """
    from jamdict import Jamdict

    jmd = Jamdict()
    master: dict[int, dict] = {}

    # Process JLPT entries (already have JMdict seq IDs — use fast get_entry)
    print("  Enriching JLPT entries via jamdict (by ID)...")
    found = 0
    for seq, entry in jlpt_entries.items():
        jmd_entry = jmd.jmdict.get_entry(seq)
        if jmd_entry is None:
            # Fallback: look up by word (slower)
            lookup_term = entry["kanji"] or entry["kana"]
            result = jmd.lookup(lookup_term)
            if not result.entries:
                master[seq] = _build_entry_from_tanos(entry)
                continue
            jmd_entry = result.entries[0]

        built = _build_entry_from_jmdict(
            jmd_entry, stage=None, source=entry["source"],
            fallback_english=entry.get("english", ""),
        )
        if built is None:
            master[seq] = _build_entry_from_tanos(entry)
            continue
        master[jmd_entry.idseq] = built
        found += 1

    print(f"  JMdict enriched: {found}/{len(jlpt_entries)} JLPT entries")

    # Process textbook entries — match to JMdict by word/reading
    print("  Matching textbook entries to JMdict...")
    tb_matched = 0
    tb_new = 0
    for tb in textbook_entries:
        word = tb["word"]
        reading = tb["reading"]

        # Try to find in JMdict (use fast search)
        results = jmd.jmdict.search(word)

        matched_entry = None
        matched_seq = None

        if results:
            # Try to find best match by reading
            for e in results:
                e_kanji = [k.text for k in e.kanji_forms]
                e_kana = [k.text for k in e.kana_forms]
                # Match by kanji form
                if word in e_kanji:
                    if not reading or reading in e_kana:
                        matched_entry = e
                        matched_seq = e.idseq
                        break
                # Match by kana form (for kana-only words)
                if word in e_kana:
                    matched_entry = e
                    matched_seq = e.idseq
                    break
            if not matched_entry:
                matched_entry = results[0]
                matched_seq = matched_entry.idseq

        tb_data = {
            "chapter": tb["chapter"],
            "pitch": tb["pitch"],
            "stage": tb["stage"],
        }

        if matched_entry and matched_seq:
            if matched_seq in master:
                # Already have this entry — add textbook data
                if master[matched_seq]["textbook"] is None:
                    master[matched_seq]["textbook"] = tb_data
                tb_matched += 1
            else:
                built = _build_entry_from_jmdict(
                    matched_entry, stage=None, source="textbook",
                    fallback_english=tb["english"],
                    textbook_data=tb_data,
                )
                if built:
                    master[matched_seq] = built
                    tb_new += 1
        else:
            # Can't find in JMdict — create a minimal entry
            # Use a negative ID to avoid collisions
            fallback_seq = -(hash(word) % 10_000_000)
            if fallback_seq not in master:
                all_forms = {word}
                if reading:
                    all_forms.add(reading)
                    kata = _hiragana_to_katakana(reading)
                    if kata != reading:
                        all_forms.add(kata)

                master[fallback_seq] = {
                    "id": fallback_seq,
                    "kanji": word,
                    "reading": reading,
                    "all_forms": sorted(all_forms),
                    "english": tb["english"],
                    "pos": [tb["pos"]] if tb["pos"] else [],
                    "stage": None,
                    "freq_rank": None,
                    "source": "textbook",
                    "textbook": tb_data,
                }
                tb_new += 1

    print(f"  Textbook: {tb_matched} matched existing, {tb_new} new entries")
    return master


def _build_entry_from_jmdict(
    jmd_entry, stage: int, source: str,
    fallback_english: str = "",
    textbook_data: dict | None = None,
) -> dict:
    """Build a master entry from a JMDict entry object."""
    kanji_forms = [k.text for k in jmd_entry.kanji_forms]
    kana_forms = [k.text for k in jmd_entry.kana_forms]

    all_forms = set(kanji_forms + kana_forms)
    for kf in kana_forms:
        kata = _hiragana_to_katakana(kf)
        if kata != kf:
            all_forms.add(kata)

    pos_tags = []
    english_glosses = []
    for sense in jmd_entry.senses:
        for p in sense.pos:
            short = _shorten_pos(str(p))
            if short and short not in pos_tags:
                pos_tags.append(short)
        for g in sense.gloss:
            if str(g) not in english_glosses:
                english_glosses.append(str(g))

    primary_kanji = kanji_forms[0] if kanji_forms else (kana_forms[0] if kana_forms else "")
    primary_reading = kana_forms[0] if kana_forms else ""

    if not primary_kanji and not primary_reading:
        return None

    return {
        "id": jmd_entry.idseq,
        "kanji": primary_kanji,
        "reading": primary_reading,
        "all_forms": sorted(all_forms),
        "english": "; ".join(english_glosses[:5]) if english_glosses else fallback_english,
        "pos": pos_tags[:4],
        "stage": stage,
        "freq_rank": None,
        "source": source,
        "textbook": textbook_data,
    }


def _build_entry_from_tanos(entry: dict) -> dict:
    """Build a master entry from tanos data alone (no JMdict match)."""
    word = entry["kanji"] or entry["kana"]
    reading = entry["kana"]
    all_forms = {word}
    if reading:
        all_forms.add(reading)
        kata = _hiragana_to_katakana(reading)
        if kata != reading:
            all_forms.add(kata)

    return {
        "id": entry["jmdict_seq"],
        "kanji": word,
        "reading": reading,
        "all_forms": sorted(all_forms),
        "english": entry.get("english", ""),
        "pos": [],
        "stage": None,
        "freq_rank": None,
        "source": entry["source"],
        "textbook": None,
    }


def _shorten_pos(pos_str: str) -> str:
    """Convert JMdict POS strings to short tags."""
    mapping = {
        "Ichidan verb": "v1",
        "Godan verb": "v5",
        "transitive verb": "vt",
        "intransitive verb": "vi",
        "noun": "n",
        "adjective (keiyoushi)": "adj-i",
        "adjectival nouns or quasi-adjectives": "adj-na",
        "na-adjective": "adj-na",
        "adverb": "adv",
        "particle": "prt",
        "conjunction": "conj",
        "interjection": "int",
        "counter": "ctr",
        "prefix": "pref",
        "suffix": "suf",
        "pronoun": "pn",
        "auxiliary verb": "v-aux",
        "auxiliary": "aux",
        "expressions": "exp",
        "Suru verb": "vs",
        "pre-noun adjectival": "adj-pn",
        "copula": "cop",
        "numeric": "num",
    }
    pos_lower = pos_str.lower()
    for key, val in mapping.items():
        if key.lower() in pos_lower:
            return val
    return ""


# ---------------------------------------------------------------------------
# 5. Assign JPDB frequency ranks AND stages
# ---------------------------------------------------------------------------

# Frequency rank → stage mapping (primary stage assignment)
# These bands determine when a word becomes available based on how
# common it is in anime/drama/LN/VN media (JPDB corpus).
FREQ_STAGE_BANDS = [
    (1500, 1),    # Top 1500 → stage 1
    (3500, 2),    # 1501-3500 → stage 2
    (7000, 3),    # 3501-7000 → stage 3
    (14000, 4),   # 7001-14000 → stage 4
    (25000, 5),   # 14001-25000 → stage 5
    (999999, 6),  # 25001+ → stage 6
]


def _rank_to_stage(rank: int) -> int:
    """Map JPDB frequency rank to stage."""
    for cutoff, stage in FREQ_STAGE_BANDS:
        if rank <= cutoff:
            return stage
    return 6


def assign_freq_ranks_and_stages(master: dict[int, dict], jpdb: dict) -> None:
    """Match each entry against JPDB, assign rank AND stage from frequency.

    Stage assignment priority:
      1. JPDB frequency rank → stage (primary)
      2. Textbook stage (can pull to earlier stage, never push later)
      3. Entries with no frequency data: use textbook stage or stage 6
    """
    matched = 0
    for entry in master.values():
        # Try primary kanji + reading
        rank = jpdb_rank_for(jpdb, entry["kanji"], entry["reading"])
        if rank is None:
            # Try each form
            for form in entry["all_forms"]:
                rank = jpdb_rank_for(jpdb, form, entry["reading"])
                if rank is not None:
                    break
                rank = jpdb_rank_for(jpdb, form, "")
                if rank is not None:
                    break
        if rank is not None:
            entry["freq_rank"] = rank
            freq_stage = _rank_to_stage(rank)
            matched += 1
        else:
            freq_stage = None

        # Determine final stage
        tb = entry.get("textbook")
        tb_stage = tb["stage"] if tb else None

        if freq_stage is not None:
            # Frequency is primary; textbook can pull earlier but not push later
            if tb_stage is not None and tb_stage < freq_stage:
                entry["stage"] = tb_stage
            else:
                entry["stage"] = freq_stage
        elif tb_stage is not None:
            # No frequency data, use textbook stage
            entry["stage"] = tb_stage
        else:
            # No frequency, no textbook — stage 6 (advanced/rare)
            entry["stage"] = 6

    print(f"  JPDB freq matched: {matched}/{len(master)} entries")
    print(f"  Stage assignment: frequency-primary, textbook can pull earlier")


# ---------------------------------------------------------------------------
# 6. Apply overrides
# ---------------------------------------------------------------------------


def apply_overrides(master: dict[int, dict]) -> None:
    """Apply manual stage overrides from overrides.json.

    Supports two formats:
      - "overrides": {jmdict_seq: stage} — by JMdict ID
      - "by_kanji": [{kanji, target_stage, reason}] — by kanji form
    """
    if not OVERRIDES_JSON.exists():
        return
    data = json.loads(OVERRIDES_JSON.read_text(encoding="utf-8"))

    # Apply by-seq overrides
    overrides = data.get("overrides", {})
    applied = 0
    for seq_str, stage in overrides.items():
        seq = int(seq_str)
        if seq in master:
            master[seq]["stage"] = stage
            master[seq]["source"] = "manual"
            applied += 1

    # Apply by-kanji overrides
    by_kanji = data.get("by_kanji", [])
    if by_kanji:
        # Build kanji → seq index for fast lookup
        kanji_index: dict[str, int] = {}
        for seq, entry in master.items():
            k = entry["kanji"]
            if k not in kanji_index:
                kanji_index[k] = seq
            for form in entry.get("all_forms", []):
                if form not in kanji_index:
                    kanji_index[form] = seq

        for override in by_kanji:
            kanji = override["kanji"]
            target = override["target_stage"]
            seq = kanji_index.get(kanji)
            if seq is not None and seq in master:
                old_stage = master[seq]["stage"]
                if old_stage is None or target < old_stage:
                    master[seq]["stage"] = target
                    master[seq]["source"] = "manual"
                    applied += 1

    if applied:
        print(f"  Overrides applied: {applied}")


# ---------------------------------------------------------------------------
# 7. Gap-fill stages
# ---------------------------------------------------------------------------


def gap_fill(master: dict[int, dict], jpdb: dict) -> None:
    """Fill stages that are under their vocab targets using JPDB-ranked JMdict entries.

    Strategy: iterate JPDB entries in rank order. For each rank band (stage hint),
    if that stage still needs entries, do a jamdict lookup and add it.
    This processes entries in a single pass through JPDB sorted by rank,
    only doing lookups until all stages are filled.
    """
    from jamdict import Jamdict

    jmd = Jamdict()

    # Count current entries per stage
    stage_counts = {s: 0 for s in range(1, 7)}
    for entry in master.values():
        if entry["stage"] in stage_counts:
            stage_counts[entry["stage"]] += 1

    print("\n  Pre-gap-fill counts:")
    for s in range(1, 7):
        target = STAGE_TARGETS[s]
        print(f"    Stage {s}: {stage_counts[s]:>5} / {target}")

    # Build set of already-known terms to skip fast without jamdict lookup
    known_terms: set[str] = set()
    assigned_ids: set[int] = set()
    for seq, entry in master.items():
        assigned_ids.add(seq)
        known_terms.add(entry["kanji"])
        if entry["reading"]:
            known_terms.add(entry["reading"])
        for f in entry.get("all_forms", []):
            known_terms.add(f)

    # Build sorted JPDB list (only entries up to the max rank we care about)
    max_rank = FREQ_STAGE_BANDS[-1][0]  # last band cutoff
    if max_rank >= 999999:
        max_rank = 50000  # practical limit for gap-filling
    jpdb_sorted = sorted(
        [(rank, term, reading) for (term, reading), rank in jpdb.items()
         if rank <= max_rank],
        key=lambda x: x[0],
    )
    print(f"\n  JPDB candidates for gap-fill: {len(jpdb_sorted):,} (rank ≤ {max_rank})")

    # How many more we need per stage
    needed = {s: max(0, STAGE_TARGETS[s] - stage_counts[s]) for s in range(1, 7)}
    total_needed = sum(needed.values())
    if total_needed == 0:
        print("  All stages already at target!")
        return

    print(f"  Total entries needed: {total_needed}")
    added_per_stage = {s: 0 for s in range(1, 7)}
    lookups = 0

    for rank, term, reading in jpdb_sorted:
        if total_needed <= 0:
            break

        stage_hint = _rank_to_stage(rank)
        if needed[stage_hint] <= 0:
            continue

        # Fast skip: if term is already known
        if term in known_terms:
            continue

        # Skip single-char non-kanji (particles etc.)
        if len(term) <= 1 and not any(
            0x4E00 <= ord(c) <= 0x9FFF for c in term
        ):
            continue

        # JMdict lookup (use fast search method)
        lookups += 1
        results = jmd.jmdict.search(term)
        if not results:
            continue

        # Find the right entry
        jmd_entry = None
        for e in results:
            e_forms = set(
                [k.text for k in e.kanji_forms]
                + [k.text for k in e.kana_forms]
            )
            if term in e_forms and e.idseq not in assigned_ids:
                jmd_entry = e
                break

        if jmd_entry is None:
            continue

        seq = jmd_entry.idseq
        kanji_forms = [k.text for k in jmd_entry.kanji_forms]
        kana_forms = [k.text for k in jmd_entry.kana_forms]

        all_forms = set(kanji_forms + kana_forms)
        for kf in kana_forms:
            kata = _hiragana_to_katakana(kf)
            if kata != kf:
                all_forms.add(kata)

        pos_tags = []
        english_glosses = []
        for sense in jmd_entry.senses:
            for p in sense.pos:
                short = _shorten_pos(str(p))
                if short and short not in pos_tags:
                    pos_tags.append(short)
            for g in sense.gloss:
                if str(g) not in english_glosses:
                    english_glosses.append(str(g))

        primary_kanji = kanji_forms[0] if kanji_forms else (kana_forms[0] if kana_forms else "")
        primary_reading = kana_forms[0] if kana_forms else ""

        if not primary_kanji:
            continue

        master[seq] = {
            "id": seq,
            "kanji": primary_kanji,
            "reading": primary_reading,
            "all_forms": sorted(all_forms),
            "english": "; ".join(english_glosses[:5]),
            "pos": pos_tags[:4],
            "stage": stage_hint,
            "freq_rank": rank,
            "source": "freq_inferred",
            "textbook": None,
        }
        assigned_ids.add(seq)
        known_terms.update(all_forms)
        needed[stage_hint] -= 1
        total_needed -= 1
        added_per_stage[stage_hint] += 1

    print(f"\n  Gap-fill complete ({lookups:,} JMdict lookups):")
    for s in range(1, 7):
        if added_per_stage[s]:
            print(f"    Stage {s}: +{added_per_stage[s]} entries")


# ---------------------------------------------------------------------------
# 8. Build and write
# ---------------------------------------------------------------------------


def build_master():
    """Main build pipeline."""
    print("=" * 60)
    print("Building master_vocab.json")
    print("=" * 60)

    # Load sources
    print("\n[1/6] Loading JPDB frequency data...")
    jpdb = load_jpdb()

    print("\n[2/6] Loading JLPT lists...")
    jlpt = load_jlpt()

    print("\n[3/6] Loading textbook appendices...")
    textbook = load_textbook()

    print("\n[4/6] Enriching with JMdict (jamdict)...")
    master = enrich_with_jamdict(jlpt, textbook)

    print("\n[5/7] Assigning JPDB frequency ranks and stages...")
    assign_freq_ranks_and_stages(master, jpdb)

    print("\n[6/7] Applying manual overrides...")
    apply_overrides(master)

    print("\n[7/7] Gap-filling stages under target...")
    gap_fill(master, jpdb)

    # Sort by (stage, freq_rank) — entries without freq_rank go to end
    entries = sorted(
        master.values(),
        key=lambda e: (e["stage"], e["freq_rank"] if e["freq_rank"] else 999999),
    )

    # Write output
    OUTPUT_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Coverage report
    print("\n" + "=" * 60)
    print("COVERAGE REPORT")
    print("=" * 60)
    stage_counts: dict[int, int] = {}
    for e in entries:
        s = e["stage"]
        stage_counts[s] = stage_counts.get(s, 0) + 1

    total = 0
    for s in range(1, 7):
        count = stage_counts.get(s, 0)
        target = STAGE_TARGETS[s]
        status = "✓" if count >= target else f"({target - count} short)"
        print(f"  Stage {s}: {count:>5} entries (target {target:>5}) {status}")
        total += count

    print(f"\n  Total: {total:,} entries")

    # Freq coverage
    with_freq = sum(1 for e in entries if e["freq_rank"])
    print(f"  With JPDB rank: {with_freq:,} ({100*with_freq/max(total,1):.1f}%)")
    with_textbook = sum(1 for e in entries if e["textbook"])
    print(f"  From textbook: {with_textbook:,}")

    # Spot checks
    print("\n  Spot checks:")
    checks = [
        ("心配", 225),
        ("テスト", 3347),
        ("おにぎり", 8994),
        ("うれしい", 1300),
        ("食べる", 184),
    ]
    form_index = {}
    for e in entries:
        for f in e["all_forms"]:
            if f not in form_index:
                form_index[f] = e

    for word, expected_rank in checks:
        e = form_index.get(word)
        if e:
            print(
                f"    {word}: stage {e['stage']}, "
                f"rank {e['freq_rank'] or '?'} (expected ~{expected_rank})"
            )
        else:
            print(f"    {word}: NOT FOUND ✗")

    print(f"\n  Written to: {OUTPUT_PATH}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    build_master()
