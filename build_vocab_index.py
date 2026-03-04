#!/usr/bin/env python3
"""
Build a cumulative vocabulary index from all stage appendix_a files,
cross-referenced with the Jitendex (Yomitan) dictionary.

Usage:
    1. Extract Jitendex zip to /tmp/jitendex/
    2. Run: python3 build_vocab_index.py
    3. Output: vocabulary_index.md
"""

import json
import os
import re
import glob

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DICT_DIR = "/tmp/jitendex"


def load_jitendex():
    """Load all Jitendex term banks into a lookup dict."""
    print("Loading Jitendex dictionary...")
    dictionary = {}

    term_files = sorted(glob.glob(os.path.join(DICT_DIR, "term_bank_*.json")))
    print(f"  Found {len(term_files)} term bank files")

    for tf in term_files:
        with open(tf, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        for entry in entries:
            word = entry[0]
            reading = entry[1]
            glosses = entry[5]
            key = (word, reading)
            if key not in dictionary:
                dictionary[key] = []
            dictionary[key].append(glosses)

    print(f"  Loaded {len(dictionary)} unique entries")
    return dictionary


def extract_first_gloss(glosses_list):
    """Get the first clean English gloss from Yomitan structured content."""
    for glosses in glosses_list:
        for gloss in glosses:
            if isinstance(gloss, str):
                return gloss.strip()
            elif isinstance(gloss, dict):
                items = collect_glossary_items(gloss)
                if items:
                    return '; '.join(items[:3])
    return ''


def collect_glossary_items(obj):
    results = []
    _walk_for_glossary(obj, results)
    return results


def _walk_for_glossary(obj, results):
    if isinstance(obj, str):
        return
    if isinstance(obj, list):
        for item in obj:
            _walk_for_glossary(item, results)
        return
    if not isinstance(obj, dict):
        return

    content_type = obj.get('type', '')
    if content_type == 'structured-content':
        _walk_for_glossary(obj.get('content', ''), results)
        return

    data = obj.get('data', {})
    if isinstance(data, dict):
        data_content = data.get('content', '')
        if data_content in ('attribution', 'extra-info', 'xref', 'xref-content',
                            'xref-glossary', 'part-of-speech-info', 'misc-info'):
            return
        if data_content == 'glossary':
            text = _extract_li_texts(obj.get('content', ''))
            results.extend(text)
            return

    tag = obj.get('tag', '')
    content = obj.get('content', '')
    if tag == 'rt':
        return
    _walk_for_glossary(content, results)


def _extract_li_texts(obj):
    items = []
    if isinstance(obj, str):
        s = obj.strip()
        if s:
            items.append(s)
        return items
    if isinstance(obj, list):
        for item in obj:
            items.extend(_extract_li_texts(item))
        return items
    if isinstance(obj, dict):
        tag = obj.get('tag', '')
        content = obj.get('content', '')
        if tag == 'li':
            text = _get_all_text(content)
            if text:
                items.append(text)
        elif tag == 'rt':
            pass
        else:
            items.extend(_extract_li_texts(content))
    return items


def _get_all_text(obj):
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        parts = [_get_all_text(item) for item in obj]
        return ''.join(p for p in parts if p)
    if isinstance(obj, dict):
        tag = obj.get('tag', '')
        if tag == 'rt':
            return ''
        data = obj.get('data', {})
        if isinstance(data, dict):
            dc = data.get('content', '')
            if dc in ('extra-info', 'xref', 'attribution'):
                return ''
        return _get_all_text(obj.get('content', ''))
    return ''


def lookup_word(dictionary, word, reading=''):
    for key_attempt in [
        (word, reading) if reading else None,
        (word, ''),
        (word, word),
        (reading, '') if reading else None,
        (reading, reading) if reading else None,
    ]:
        if key_attempt and key_attempt in dictionary:
            return extract_first_gloss(dictionary[key_attempt])

    for (w, r), glosses in dictionary.items():
        if w == word:
            return extract_first_gloss(glosses)

    if reading:
        for (w, r), glosses in dictionary.items():
            if r == reading and w != reading:
                return extract_first_gloss(glosses)

    return ''


def parse_vocab(filepath, stage_num):
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('|') or re.match(r'\|[\s-]+\|', line):
            continue

        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]

        if len(parts) < 3:
            continue

        if parts[0] in ('Word', 'Japanese', '単語', 'Kanji'):
            continue

        if len(parts) >= 6:
            entries.append({
                'word': parts[0],
                'reading': parts[1].replace('—', '').replace('–', '').strip(),
                'pitch': parts[2],
                'pos': parts[3],
                'english': parts[4],
                'chapter': parts[5],
                'stage': stage_num
            })
        elif len(parts) >= 4:
            entries.append({
                'word': parts[0],
                'reading': parts[1].replace('—', '').replace('–', '').strip(),
                'pitch': parts[2],
                'pos': '',
                'english': parts[3],
                'chapter': '',
                'stage': stage_num
            })
        elif len(parts) >= 3:
            entries.append({
                'word': parts[0],
                'reading': '',
                'pitch': parts[1],
                'pos': '',
                'english': parts[2],
                'chapter': '',
                'stage': stage_num
            })

    return entries


def jlpt_level_for_stage(stage):
    return {1: 'N5', 2: 'N4', 3: 'N3', 4: 'N2', 5: 'N1', 6: 'N1+'}.get(stage, '—')


def main():
    dictionary = load_jitendex()

    all_entries = []
    for stage_num in range(1, 7):
        filepath = os.path.join(PROJECT_DIR, f'stage{stage_num}', 'appendix_a_vocabulary.md')
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping")
            continue
        print(f"Parsing Stage {stage_num} vocabulary...")
        entries = parse_vocab(filepath, stage_num)
        print(f"  Found {len(entries)} entries")
        all_entries.extend(entries)

    print(f"\nTotal entries across all stages: {len(all_entries)}")
    print("\nLooking up words in Jitendex...")

    found_count = 0
    for entry in all_entries:
        dict_def = lookup_word(dictionary, entry['word'], entry['reading'])
        if dict_def:
            found_count += 1
            if len(dict_def) > 100:
                cut = dict_def[:100].rfind(';')
                if cut == -1:
                    cut = dict_def[:100].rfind(',')
                if cut == -1:
                    cut = 97
                dict_def = dict_def[:cut].rstrip(',; ') + '...'
            entry['dict_english'] = dict_def
        else:
            entry['dict_english'] = entry['english']

    print(f"  Found {found_count}/{len(all_entries)} words in dictionary")

    seen = {}
    unique_entries = []
    for entry in all_entries:
        key = (entry['word'], entry['reading'])
        if key not in seen:
            seen[key] = True
            unique_entries.append(entry)

    print(f"  After dedup: {len(unique_entries)} unique entries")

    def sort_key(entry):
        reading = entry['reading'] if entry['reading'] else entry['word']
        result = ''
        for ch in reading:
            cp = ord(ch)
            if 0x30A0 <= cp <= 0x30FF:
                result += chr(cp - 0x60)
            else:
                result += ch
        return result

    unique_entries.sort(key=sort_key)

    print("\nGenerating vocabulary_index.md...")

    kana_rows = [
        ('あ', 'あいうえお'), ('か', 'かきくけこがぎぐげご'),
        ('さ', 'さしすせそざじずぜぞ'), ('た', 'たちつてとだぢづでど'),
        ('な', 'なにぬねの'), ('は', 'はひふへほばびぶべぼぱぴぷぺぽ'),
        ('ま', 'まみむめも'), ('や', 'やゆよ'),
        ('ら', 'らりるれろ'), ('わ', 'わをん'),
    ]

    def get_row_label(entry):
        reading = entry['reading'] if entry['reading'] else entry['word']
        if not reading:
            return 'Other'
        first = reading[0]
        cp = ord(first)
        if 0x30A0 <= cp <= 0x30FF:
            first = chr(cp - 0x60)
        for label, chars in kana_rows:
            if first in chars:
                return label
        return 'Other'

    lines = [
        "# Cumulative Vocabulary Index", "",
        "This index consolidates every vocabulary item across all six stages of 道. Definitions are sourced from the **Jitendex** dictionary (based on JMdict) and edited for conciseness.", "",
        "---", "",
        "## How to Read This Index", "",
        "| Column | Description |",
        "|--------|-------------|",
        "| **Word** | The word as written (kanji where applicable) |",
        "| **Reading** | Kana reading (blank if word is already kana) |",
        "| **Pitch** | Pitch accent: ⓪ = heiban (flat), ①②③… = downstep after that mora |",
        "| **POS** | Part of speech |",
        "| **English** | English definition (from Jitendex / JMdict) |",
        "| **JLPT** | Approximate JLPT level based on stage of introduction |",
        "| **Stage.Ch** | Stage and chapter of first introduction |",
        "", "---", "",
    ]

    current_row = None
    for entry in unique_entries:
        row = get_row_label(entry)
        if row != current_row:
            current_row = row
            lines.append(f"## {row}行")
            lines.append("")
            lines.append("| Word | Reading | Pitch | POS | English | JLPT | Stage.Ch |")
            lines.append("|------|---------|-------|-----|---------|------|----------|")

        word = entry['word']
        reading = entry['reading'] if entry['reading'] else '—'
        pitch = entry['pitch'] if entry['pitch'] else '—'
        pos = entry['pos'] if entry['pos'] else '—'
        english = (entry['dict_english'] or entry['english']).replace('|', '/')
        jlpt = jlpt_level_for_stage(entry['stage'])
        stage_ch = f"{entry['stage']}.{entry['chapter']}" if entry['chapter'] else f"{entry['stage']}"

        lines.append(f"| {word} | {reading} | {pitch} | {pos} | {english} | {jlpt} | {stage_ch} |")

    lines.extend(["", "---", "",
        f"*Total entries: {len(unique_entries)}. Definitions sourced from Jitendex (JMdict). Pitch accent from 道 textbook.*", ""])

    output_path = os.path.join(PROJECT_DIR, 'vocabulary_index.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Written to {output_path}")
    print(f"Total unique entries: {len(unique_entries)}")


if __name__ == '__main__':
    main()
