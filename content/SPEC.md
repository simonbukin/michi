# Michi Parallel Content System — Technical Specification

## Overview

This system generates a parallel reading and audio track to accompany the Michi
Japanese grammar curriculum. For each Michi stage (1–6, corresponding to N5–N1),
it produces:

- **Graded readers** as EPUBs: vocabulary-controlled Japanese stories with
  furigana, chapter-end glossaries, and grammar notes. Designed for KOReader
  on Kobo. Static, no interactivity required.

- **Audio dialogues** as MP3s: vocabulary-controlled Japanese dialogue between
  recurring characters, synthesized via AivisSpeech (Style-BERT-VITS2). Each
  MP3 is accompanied by a self-contained HTML file with word-level synchronized
  transcript.

Both tracks share a vocabulary ledger and are gated by Michi stage. All
vocabulary and grammar enforcement is mechanical (MeCab + rule engine). The LLM
(Claude API) is used only for creative generation — outlines and prose — never
for rule enforcement.

---

## Content Format: Episodic / Situational

Content follows a manga/anime episodic structure, not a serialized plot.

**Same cast, different situations per episode.** Each episode is self-contained.
No plot continuity is required between episodes. Characters have consistent
voice and personality but no tracked fact state.

This is intentional. It eliminates the story coherence and state-tracking
problems that plague serialized LLM generation. An episode about going to the
supermarket requires knowing that Aoi is curious and informal — not what happened
to her last Tuesday.

**Arc clustering** groups episodes loosely by situation type:
- Daily life arc (home, food, transport)
- School/work arc (campus, part-time jobs, study)
- Seasonal arc (spring events, summer, autumn, winter)
- Social arc (meeting friends, family, small conflicts)

Each arc contains 8–15 episodes. Arc identity is cosmetic — it affects the
situation pool used for generation, not any narrative state.

**Character state** is limited to:
- Name, age, relationship to other characters
- Personality descriptors (2–3 adjectives)
- Speech style description (particles, register, verbal tics)
- Situation blacklist (recently used situations, to avoid repetition)

This fits in ~30 lines of JSON per character. It is the only "memory" the
generation system needs.

---

## System Components

```
michi-content/
├── SPEC.md                        # this file
├── config/
│   ├── stages.json                # Michi stage definitions (grammar, vocab targets)
│   ├── characters.json            # cast personality cards
│   └── situation_pools.json       # situational templates per arc/stage
├── ledger/
│   └── vocab_ledger.json          # vocabulary state (counts, stage, last seen)
├── rule_engine/
│   ├── vocab_checker.py           # MeCab-based vocabulary validation
│   ├── grammar_tagger.py          # regex grammar pattern checker
│   └── complexity_scorer.py       # sentence length / subordination depth
├── annotator/
│   ├── furigana.py                # furigana generation via fugashi + UniDic
│   ├── glosser.py                 # JMDict English gloss lookup
│   └── grammar_noter.py          # grammar pattern annotation
├── generator/
│   ├── outline_gen.py             # Step 1: JSON outline from Claude
│   ├── prose_gen.py               # Step 2: Japanese text from outline
│   └── correction_gen.py          # Step 3: targeted correction on violations
├── tts/
│   ├── synthesizer.py             # AivisSpeech API calls, per-turn WAV
│   ├── aligner.py                 # stable-ts forced alignment
│   └── audio_builder.py           # merge turns, insert pauses, export MP3
├── exporters/
│   ├── epub_exporter.py           # EPUB builder (ebooklib)
│   └── transcript_exporter.py     # self-contained HTML transcript + player
├── orchestrator.py                # top-level pipeline runner
└── outputs/
    ├── stage1/
    │   ├── readers/               # EPUBs
    │   └── audio/                 # MP3s + HTML transcripts
    └── stage2/ ...
```

---

## Phase 0 — Foundation

### 0.1 Environment Setup

**Target platform:** Mac Mini (Apple Silicon), macOS.

**Python version:** 3.11+

**Dependencies:**

```
# NLP / tokenization
fugashi[unidic]          # MeCab Python wrapper with UniDic dictionary
unidic                   # full UniDic dictionary (requires: python -m unidic download)
jamdict                  # JMDict/JMnedict lookup (English glosses)
pykakasi                 # fallback furigana for edge cases

# Audio
requests                 # AivisSpeech API calls
pydub                    # audio segment manipulation, MP3 export
stable-whisper           # forced alignment against known transcript
ffmpeg                   # required by pydub (install via brew)

# EPUB
ebooklib                 # EPUB construction

# LLM
anthropic                # Claude API client

# Utilities
tqdm                     # progress bars for batch generation
python-dotenv            # environment variable management
```

**External services / applications:**

- AivisSpeech Engine: install from aivis-project.com, runs as local server on
  port 10101. Must be running before any TTS pipeline step.
- Claude API key: set as `ANTHROPIC_API_KEY` in `.env`.

**AivisSpeech voice models:** Download at least 2 distinct voices from AivisHub
before Phase 2. Assign one voice ID to each character in `characters.json`.
Voice IDs are integers (e.g., 888753760 for Anneli ノーマル).

### 0.2 Configuration Files

**`config/stages.json`** — one entry per Michi stage:

```json
{
  "1": {
    "jlpt": "N5",
    "vocab_target": 800,
    "kanji_target": 100,
    "grammar_ceiling": [
      "masu_form", "te_form", "te_iru", "te_kudasai",
      "nai_form", "ta_form", "i_adjective", "na_adjective",
      "basic_particles", "tai", "mashou", "nakereba_naranai",
      "deshou", "to_omou"
    ],
    "audio_speed_scale": 0.45,
    "audio_intonation_scale": 1.2,
    "inter_turn_pause_ms": 1500,
    "furigana_threshold": 8,
    "max_sentence_chars": 40,
    "max_turn_mora": 20,
    "elision_allowed": false,
    "keigo_allowed": false
  },
  "2": { ... },
  "3": { ... },
  "4": { ... },
  "5": { ... },
  "6": { ... }
}
```

**`config/characters.json`** — cast cards:

```json
{
  "あおい": {
    "full_name": "田中あおい",
    "age": 20,
    "role": "大学1年生",
    "personality": ["好奇心旺盛", "少し心配性", "明るい"],
    "speech_style": "casual female; uses ね、かな、〜んだけど frequently; avoids だろう",
    "voice_id": 888753760,
    "stage_introduced": 1
  },
  "けんた": {
    "full_name": "鈴木けんた",
    "age": 22,
    "role": "大学3年生、あおいの先輩",
    "personality": ["落ち着いている", "親切", "少し頑固"],
    "speech_style": "casual male; uses よ、だろう、〜じゃないか; more formal than あおい",
    "voice_id": 888753761,
    "stage_introduced": 1
  }
}
```

Additional characters can be added at higher stages (Stage 3: a teacher or
workplace character who uses more formal register; Stage 4: keigo-using
character for workplace episodes).

**`config/situation_pools.json`** — situation templates per arc:

```json
{
  "daily_life": [
    "コンビニで何かを買おうとしている",
    "朝ごはんを食べながら話している",
    "雨が降ってきた",
    "道に迷っている"
  ],
  "school": [
    "授業の前に話している",
    "図書館で勉強しようとしている",
    "課題について相談している"
  ]
}
```

Situations are selected by the orchestrator, checked against the episode
history blacklist, and passed to the outline generator.

---

## Phase 1 — Vocabulary Ledger

The vocabulary ledger is the central state object. Both content tracks read
from and write to it. It tracks every Japanese word the learner has encountered
and how many times.

### 1.1 Data Structure

**`ledger/vocab_ledger.json`:**

```json
{
  "meta": {
    "current_stage": 1,
    "total_episodes_generated": 0,
    "total_characters_generated": 0,
    "last_updated": "2025-03-29T00:00:00"
  },
  "words": {
    "食べる": {
      "count": 23,
      "status": "active",
      "stage_introduced": 1,
      "last_seen_episode": 12
    },
    "緊張する": {
      "count": 2,
      "status": "new",
      "stage_introduced": 3,
      "last_seen_episode": 47
    }
  },
  "episode_blacklist": [
    "コンビニで買い物する",
    "雨が降ってきた"
  ]
}
```

**Word status transitions:**

```
not_seen → new (first appearance)
new → zone (count >= 3)
zone → active (count >= 10)
```

### 1.2 Ledger API (`ledger/ledger.py`)

```python
class VocabLedger:
    def load(self) -> None
    def save(self) -> None
    
    def get_status(self, lemma: str) -> str
    # Returns: "active" | "zone" | "new" | "unknown"
    
    def is_allowed(self, lemma: str, stage: int) -> bool
    # True if word is in any status AND stage_introduced <= current stage
    
    def get_active_words(self) -> list[str]
    def get_zone_words(self) -> list[str]
    
    def allocate_new_words(self, n: int, stage: int) -> list[str]
    # Returns n words from the stage vocab list not yet in ledger
    # Prioritizes high-frequency words first
    
    def record_episode(self, lemmas_seen: list[str], episode_id: str) -> None
    # Increments counts, updates statuses, updates last_seen
    
    def get_prompt_summary(self, stage: int) -> dict
    # Returns compact dict for injection into generation prompts:
    # {"zone_words": [...], "new_words_allocated": [...], 
    #  "total_active": N, "stage": N}
    
    def add_to_blacklist(self, situation: str) -> None
    def get_blacklist(self) -> list[str]
    def prune_blacklist(self, keep_last_n: int = 20) -> None
```

### 1.3 Stage Vocabulary Lists

Each Michi stage maps to a frequency-ordered vocabulary list. These are derived
from the JLPT vocabulary lists (N5 through N1) cross-referenced with the Michi
stage vocab targets. Stored as `ledger/stage_vocab/stage_N.json` — a list of
lemmas ordered by frequency, with JMDict sense IDs attached.

Source: jlpt-vocab lists (tanos.co.uk compilations), cross-referenced with
UniDic lemma forms for MeCab compatibility.

---

## Phase 2 — Rule Engine

The rule engine performs all mechanical validation. No LLM involved. Runs on
every piece of generated content before it proceeds to annotation or export.

### 2.1 Vocabulary Checker (`rule_engine/vocab_checker.py`)

Uses `fugashi` with full UniDic to tokenize generated Japanese text. For each
content word (noun, verb, adjective, adverb), checks the lemma against the
ledger.

```python
class VocabChecker:
    def __init__(self, ledger: VocabLedger, stage: int)
    
    def check(self, text: str) -> VocabCheckResult
```

```python
@dataclass
class VocabCheckResult:
    passed: bool
    violation_rate: float           # violations / total content tokens
    violations: list[VocabViolation]
    comprehension_estimate: float   # 1.0 - violation_rate
    
@dataclass
class VocabViolation:
    surface: str                    # surface form in text
    lemma: str                      # dictionary form
    position: int                   # character position in text
    stage_required: int             # what stage introduces this word
    current_stage: int
    suggestion: str | None          # simpler alternative if available
```

**Pass threshold:** `violation_rate <= 0.02` (98% comprehension floor).

**Token filtering:** Particles, conjunctions, auxiliary verbs, and proper nouns
(character names, place names) are excluded from the violation check. Only
content words count.

**Suggestion lookup:** When a violation is found, query JMDict synonyms and
return the highest-frequency synonym available at the current stage.

### 2.2 Grammar Tagger (`rule_engine/grammar_tagger.py`)

Pattern library of Japanese grammar forms, each tagged with the Michi stage
that introduces it. Uses regex on the raw text (post-tokenization context for
disambiguation where needed).

```python
class GrammarTagger:
    def check(self, text: str, stage: int) -> GrammarCheckResult
    def tag_all(self, text: str) -> list[GrammarTag]
    # Returns all grammar patterns found regardless of stage,
    # for use by the annotation pipeline
```

**Pattern library structure** (`rule_engine/grammar_patterns.json`):

```json
[
  {
    "id": "te_iru",
    "name": "〜ている",
    "stage": 1,
    "regex": "て(い|お)る|てる",
    "explanation_ja": "進行・結果を表す",
    "explanation_en": "ongoing action or resultant state"
  },
  {
    "id": "passive",
    "name": "受身形",
    "stage": 2,
    "regex": "[あかさたなはまやらわ]れ(る|た|て|ない)",
    "explanation_ja": "〜される・〜された",
    "explanation_en": "passive voice"
  },
  {
    "id": "causative_passive",
    "name": "使役受身",
    "stage": 2,
    "regex": "[させせ]られ",
    "explanation_ja": "〜させられる",
    "explanation_en": "causative-passive: was made to do"
  },
  {
    "id": "wake_da",
    "name": "〜わけだ",
    "stage": 3,
    "regex": "わけだ|わけです|わけじゃ",
    "explanation_en": "logical conclusion / so that's why"
  }
  // ... full pattern library covering all Michi stages
]
```

Full pattern library covers all grammar introduced across Michi Stages 1–6.
Approximately 80–120 patterns total.

### 2.3 Complexity Scorer (`rule_engine/complexity_scorer.py`)

Catches content that passes vocabulary and grammar checks but is still too
complex for the stage — overly long sentences, deeply nested subordination.

```python
class ComplexityScorer:
    def score(self, text: str, stage: int) -> ComplexityResult

@dataclass
class ComplexityResult:
    passed: bool
    avg_sentence_chars: float
    max_sentence_chars: int
    max_subordination_depth: int    # nested clause count
    avg_mora_per_turn: float        # for dialogue scripts
    violations: list[ComplexityViolation]
```

**Stage thresholds** (from `config/stages.json`):

| Stage | Max sentence chars | Max subordination depth | Max mora/turn |
|---|---|---|---|
| 1 | 40 | 1 | 20 |
| 2 | 70 | 2 | 30 |
| 3 | 100 | 3 | 45 |
| 4 | 150 | 4 | 60 |
| 5 | 200 | 5 | 80 |
| 6 | unlimited | unlimited | unlimited |

Subordination depth is measured by counting nested clause boundaries: relative
clauses, nominalized clauses, conditional clauses, quotation clauses.

### 2.4 Validation Runner (`rule_engine/validator.py`)

Orchestrates all three checks and returns a combined result.

```python
def validate(text: str, stage: int, content_type: str,
             ledger: VocabLedger) -> ValidationResult:

@dataclass
class ValidationResult:
    passed: bool
    vocab: VocabCheckResult
    grammar: GrammarCheckResult
    complexity: ComplexityResult
    hard_fail: bool        # True if vocab violation_rate > 0.02 or grammar violation
    soft_fail: bool        # True if only complexity violations
```

Hard fails trigger regeneration. Soft fails trigger targeted correction only
of the offending sentences.

---

## Phase 3 — Annotation Pipeline

Runs after validation passes. Produces a structured representation of the text
with all annotation data attached to each token. Used by both exporters.

### 3.1 Tokenizer + Furigana (`annotator/furigana.py`)

Uses `fugashi` with full UniDic. For each token:
- Surface form
- Lemma (dictionary form)
- Part of speech (UniDic 品詞)
- Reading (カタカナ)
- Furigana (reading applied to kanji surface only)

Furigana display rule: show furigana if the surface contains kanji AND the
word's ledger count is below the stage's `furigana_threshold` (default: 8).

```python
@dataclass
class AnnotatedToken:
    surface: str
    lemma: str
    pos: str                    # UniDic part of speech
    reading: str | None         # katakana reading
    furigana: str | None        # reading for kanji surface; None if hiragana-only
    gloss: Gloss | None         # English gloss (set by glosser)
    grammar_tags: list[GrammarTag]  # grammar patterns this token participates in
    status: str                 # "active" | "zone" | "new" | "unknown"
    footnote_id: int | None     # assigned during EPUB export
```

### 3.2 Glosser (`annotator/glosser.py`)

Uses `jamdict` to look up JMDict entries by lemma. Returns the most common
sense (sense[0], gloss[0]) unless POS context suggests otherwise.

```python
@dataclass
class Gloss:
    en: str                     # English definition
    pos: str                    # part of speech label
    notes: str | None           # usage notes if any
```

Gloss is attached only to tokens with status `new` or `zone`. Active words
are assumed known and do not receive glosses in the output.

### 3.3 Grammar Noter (`annotator/grammar_noter.py`)

Maps GrammarTagger output back to token spans. Groups multi-token grammar
patterns (e.g., てはいけない spans 3 tokens) into a single tag applied to
all participating tokens.

```python
@dataclass
class GrammarTag:
    id: str                     # pattern ID from grammar_patterns.json
    name: str                   # display name (e.g., "〜てはいけない")
    explanation_en: str
    stage: int
    token_span: tuple[int, int] # start, end indices in token list
```

### 3.4 Annotator Entry Point (`annotator/annotator.py`)

```python
def annotate(text: str, stage: int, ledger: VocabLedger) -> AnnotatedText:

@dataclass
class AnnotatedText:
    tokens: list[AnnotatedToken]
    grammar_patterns: list[GrammarTag]   # deduplicated list of patterns used
    raw: str
    stage: int
```

---

## Phase 4 — Content Generation

Two generation flows: **prose** (for readers) and **dialogue** (for audio).
Both follow the same three-step pattern:

```
Step 1: Generate JSON outline   →  structured, checkable, short
Step 2: Generate Japanese text  →  prose or dialogue from outline
Step 3: Validate + correct      →  mechanical validation, targeted LLM correction
```

The LLM never enforces rules. It only generates content. All rule checking
is in Phase 2.

### 4.1 Outline Generation (`generator/outline_gen.py`)

**For prose episodes:**

System prompt (static, not per-call):
```
You are an outline writer for Japanese graded readers.
Your outlines are used by a separate prose writer.
Output valid JSON only. No commentary, no markdown, no explanation.
```

User prompt (constructed per call):

```python
def build_outline_prompt(stage_config: dict, ledger_summary: dict,
                          characters: dict, situation: str,
                          arc: str) -> str:
    return f"""
Generate a graded reader episode outline.

STAGE: {stage_config['jlpt']}
SITUATION: {situation}
ARC: {arc}
CHARACTERS AVAILABLE: {list(characters.keys())}
NEW VOCABULARY TO INTRODUCE: {ledger_summary['new_words_allocated']}
WORDS TO REINFORCE (acquisition zone): {ledger_summary['zone_words'][:10]}

Output JSON in exactly this structure:
{{
  "title": "short episode title in Japanese",
  "characters_in_episode": ["..."],
  "setting": "brief description",
  "beat_1": "what happens first",
  "beat_2": "what develops",
  "turn": "small complication or surprising moment",
  "resolution": "how it resolves",
  "emotional_tone": "one word",
  "new_vocab_appears_in": {{
    "word1_lemma": "beat_1",
    "word2_lemma": "beat_2"
  }}
}}
"""
```

The `new_vocab_appears_in` field forces planning of vocabulary placement before
prose is written. Claude decides where each new word will naturally appear.
The prose generator then receives this plan and knows where to situate each word.

**For dialogue episodes:**

Same structure but with additional fields:
```json
{
  "turns": [
    {"character": "あおい", "beat": "opening", "content": "brief description"},
    {"character": "けんた", "beat": "response", "content": "..."}
  ],
  "aizuchi_moments": ["after beat 2", "after resolution"],
  "register_notes": "casual throughout; no keigo at this stage"
}
```

### 4.2 Prose Generation (`generator/prose_gen.py`)

Takes the validated outline and generates Japanese text.

System prompt:
```
You are a Japanese writer for graded readers.
Write natural, engaging Japanese prose.
Output Japanese text only. No romaji, no English, no commentary.
Do not add titles or headers.
```

User prompt:
```python
def build_prose_prompt(outline: dict, stage_config: dict,
                        characters: dict, ledger_summary: dict) -> str:
    char_voices = {
        name: data["speech_style"]
        for name, data in characters.items()
        if name in outline["characters_in_episode"]
    }
    
    return f"""
Write a graded reader story from this outline.

OUTLINE:
{json.dumps(outline, ensure_ascii=False, indent=2)}

CHARACTER VOICES:
{json.dumps(char_voices, ensure_ascii=False)}

GRAMMAR CEILING: {stage_config['jlpt']} level — do not use grammar beyond this
TARGET LENGTH: {TARGET_CHARS[stage_config['stage']]} characters
FURIGANA: do not add — the system adds furigana automatically
TONE: {outline['emotional_tone']}

Write the story now.
"""
```

**For dialogue scripts**, the output format is:

```
あおい:「セリフ」
けんた:「セリフ」
```

Each line is one turn. Character name followed by 「」-enclosed dialogue.
No narration, no action descriptions, no stage directions. Pure dialogue only.

### 4.3 Correction Generation (`generator/correction_gen.py`)

Called when validation produces targeted violations (hard fail on vocab/grammar).
Sends only the violating sentences with error details, not the whole text.

```python
def build_correction_prompt(original_text: str,
                             violations: list[VocabViolation],
                             stage_config: dict) -> str:
    violation_lines = []
    for v in violations:
        violation_lines.append(
            f"- 「{v.surface}」(lemma: {v.lemma}) is Stage {v.stage_required} "
            f"vocabulary, not available at Stage {v.current_stage}."
            + (f" Possible replacement: 「{v.suggestion}」" if v.suggestion else "")
        )
    
    return f"""
The following words in this text are too advanced for Stage {stage_config['jlpt']}:

{chr(10).join(violation_lines)}

Original text:
{original_text}

Rewrite only the sentences containing these words.
Replace each flagged word with a natural Stage {stage_config['jlpt']} alternative.
Do not change any other sentences.
Output the complete corrected text.
"""
```

Maximum 3 correction attempts before raising `GenerationFailure`.

### 4.4 Orchestration (`generator/generate_episode.py`)

```python
def generate_reader_episode(stage: int, arc: str,
                              ledger: VocabLedger) -> ReaderEpisode:
    situation = pick_situation(arc, stage, ledger.get_blacklist())
    
    # Step 1: outline
    outline = call_claude(build_outline_prompt(...), expect_json=True)
    
    # Step 2: prose
    raw_text = call_claude(build_prose_prompt(outline, ...))
    
    # Step 3: validate + correct
    for attempt in range(3):
        result = validate(raw_text, stage, "prose", ledger)
        if result.passed:
            break
        if result.hard_fail:
            raw_text = call_claude(build_correction_prompt(
                raw_text, result.vocab.violations, ...))
        elif result.soft_fail:
            raw_text = fix_complexity(raw_text, result.complexity)
    else:
        raise GenerationFailure(...)
    
    # Annotate
    annotated = annotate(raw_text, stage, ledger)
    
    # Update ledger
    lemmas = [t.lemma for t in annotated.tokens]
    ledger.record_episode(lemmas, episode_id)
    ledger.add_to_blacklist(situation)
    ledger.save()
    
    return ReaderEpisode(outline=outline, annotated=annotated, raw=raw_text)


def generate_audio_episode(stage: int, arc: str,
                             ledger: VocabLedger) -> AudioEpisode:
    # Same flow, produces a list of (character, line) turns
    # instead of narrative prose
    ...
```

---

## Phase 5 — Audio Synthesis

Converts a dialogue script (list of character turns) into a merged MP3 file
with word-level timestamps.

### 5.1 Turn Synthesis (`tts/synthesizer.py`)

Calls AivisSpeech local API per turn. Returns raw WAV bytes.

```python
def synthesize_turn(text: str, speaker_id: int,
                    speed_scale: float,
                    intonation_scale: float,
                    pre_phoneme_length: float = 0.05,
                    post_phoneme_length: float = 0.1) -> bytes:
    
    # POST /audio_query — get synthesis parameters
    query = requests.post(
        "http://127.0.0.1:10101/audio_query",
        params={"text": text, "speaker": speaker_id}
    ).json()
    
    query["speedScale"] = speed_scale
    query["intonationScale"] = intonation_scale
    query["prePhonemeLength"] = pre_phoneme_length
    query["postPhonemeLength"] = post_phoneme_length
    
    # POST /synthesis — get WAV bytes
    response = requests.post(
        "http://127.0.0.1:10101/synthesis",
        params={"speaker": speaker_id},
        json=query
    )
    response.raise_for_status()
    return response.content  # raw WAV bytes
```

**Stage speed/intonation settings** (from `config/stages.json`):

| Stage | speed_scale | intonation_scale | inter_turn_pause_ms |
|---|---|---|---|
| 1 | 0.45 | 1.2 | 1500 |
| 2 | 0.65 | 1.15 | 900 |
| 3 | 0.85 | 1.1 | 600 |
| 4 | 1.05 | 1.05 | 400 |
| 5 | 1.2 | 1.0 | 300 |
| 6 | 1.35 | 1.0 | 250 |

`speed_scale` is a multiplier on AivisSpeech's default speed. Default is
approximately 1.0 = natural conversational pace (~200–230 mora/min for the
Anneli voice model).

### 5.2 Forced Alignment (`tts/aligner.py`)

Uses `stable-whisper` in alignment mode (not transcription mode). Since the
input text is known exactly, this is forced alignment — the model aligns the
known text to the audio, not guessing the transcript.

On clean synthesized audio with no background noise, word-level accuracy is
within 20–50ms.

```python
import stable_whisper

_model = None

def get_model():
    global _model
    if _model is None:
        # "base" is sufficient for clean synth audio on CPU
        # Use "small" if accuracy is insufficient
        _model = stable_whisper.load_model("base")
    return _model

def align_turn(wav_bytes: bytes, known_text: str) -> list[WordTimestamp]:
    """
    Forced alignment of known_text against wav_bytes.
    Returns word-level timestamps.
    """
    model = get_model()
    
    # stable-ts align() takes audio + transcript
    result = model.align(
        wav_bytes,
        known_text,
        language="ja"
    )
    
    timestamps = []
    for segment in result.segments:
        for word in segment.words:
            timestamps.append(WordTimestamp(
                word=word.word,
                start_ms=int(word.start * 1000),
                end_ms=int(word.end * 1000)
            ))
    
    return timestamps

@dataclass
class WordTimestamp:
    word: str
    start_ms: int
    end_ms: int
```

### 5.3 Audio Builder (`tts/audio_builder.py`)

Synthesizes all turns, aligns each, merges into final MP3, accumulates
timestamps with offsets.

```python
from pydub import AudioSegment
import io

def build_episode_audio(script: list[DialogueTurn],
                         stage_config: dict,
                         characters: dict) -> AudioPackage:
    
    audio_segments = []
    all_timestamps = []
    current_offset_ms = 0
    pause_ms = stage_config["inter_turn_pause_ms"]
    
    for turn in script:
        char = turn.character
        text = turn.text
        speaker_id = characters[char]["voice_id"]
        
        # Synthesize
        wav_bytes = synthesize_turn(
            text=text,
            speaker_id=speaker_id,
            speed_scale=stage_config["audio_speed_scale"],
            intonation_scale=stage_config["audio_intonation_scale"]
        )
        
        seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        
        # Forced alignment against known text
        word_times = align_turn(wav_bytes, text)
        
        # Offset timestamps
        for wt in word_times:
            all_timestamps.append({
                "word": wt.word,
                "character": char,
                "start_ms": wt.start_ms + current_offset_ms,
                "end_ms": wt.end_ms + current_offset_ms
            })
        
        audio_segments.append(seg)
        current_offset_ms += len(seg)
        
        # Inter-turn pause
        pause = AudioSegment.silent(duration=pause_ms)
        audio_segments.append(pause)
        current_offset_ms += pause_ms
    
    # Merge all segments
    full_audio = sum(audio_segments)
    mp3_bytes = full_audio.export(format="mp3", bitrate="128k").read()
    
    return AudioPackage(
        mp3=mp3_bytes,
        timestamps=all_timestamps,
        duration_ms=current_offset_ms
    )

@dataclass
class AudioPackage:
    mp3: bytes
    timestamps: list[dict]   # [{word, character, start_ms, end_ms}]
    duration_ms: int
```

---

## Phase 6 — EPUB Export

Produces a static EPUB for KOReader on Kobo. No interactivity. KOReader
supports ruby annotations (furigana) and footnotes. Glosses appear at chapter
end as footnotes, not inline.

### 6.1 HTML Rendering (`exporters/epub_exporter.py`)

```python
def render_chapter_html(annotated: AnnotatedText) -> str:
    body_parts = []
    footnotes = []
    fn_counter = 0
    glossed_lemmas = set()  # one gloss per lemma per chapter
    
    for token in annotated.tokens:
        surface = token.surface
        
        # Build ruby (furigana) if needed
        if token.furigana:
            core = f'<ruby>{surface}<rt>{token.furigana}</rt></ruby>'
        else:
            core = surface
        
        # Footnote for new/zone words (first occurrence only)
        if (token.gloss and
            token.status in ("new", "zone") and
            token.lemma not in glossed_lemmas):
            
            fn_counter += 1
            glossed_lemmas.add(token.lemma)
            
            reading_str = f"[{token.furigana}] " if token.furigana else ""
            grammar_str = ""
            if token.grammar_tags:
                tag = token.grammar_tags[0]
                grammar_str = f" • {tag.name}: {tag.explanation_en}"
            
            footnotes.append(
                f'<p id="fn{fn_counter}" class="gloss-entry">'
                f'<sup>{fn_counter}</sup> '
                f'<span class="gloss-word">{surface}</span> '
                f'<span class="gloss-reading">{reading_str}</span>'
                f'<span class="gloss-en">{token.gloss.en}</span>'
                f'<span class="gloss-grammar">{grammar_str}</span>'
                f'</p>'
            )
            body_parts.append(
                f'<sup><a id="fnref{fn_counter}" '
                f'href="#fn{fn_counter}">{fn_counter}</a></sup>{core}'
            )
        else:
            body_parts.append(core)
    
    # Grammar summary section — one entry per unique pattern used
    grammar_section = ""
    if annotated.grammar_patterns:
        items = []
        for pat in annotated.grammar_patterns:
            items.append(
                f'<p class="grammar-entry">'
                f'<span class="grammar-name">{pat.name}</span> — '
                f'{pat.explanation_en}'
                f'</p>'
            )
        grammar_section = (
            '<div class="grammar-section">'
            '<h3 class="section-header">文法メモ</h3>'
            + "".join(items) +
            '</div>'
        )
    
    gloss_section = ""
    if footnotes:
        gloss_section = (
            '<div class="gloss-section">'
            '<h3 class="section-header">語句</h3>'
            + "".join(footnotes) +
            '</div>'
        )
    
    return (
        '<div class="story-body">' + "".join(body_parts) + '</div>'
        + grammar_section
        + gloss_section
    )
```

### 6.2 CSS (KOReader-compatible)

```css
/* epub_style.css */

body {
    font-family: serif;
    line-height: 1.8;
    font-size: 1em;
}

.story-body {
    margin-bottom: 3em;
}

ruby rt {
    font-size: 0.55em;
    color: #666;
}

sup a {
    font-size: 0.6em;
    color: #888;
    text-decoration: none;
}

.section-header {
    font-size: 0.9em;
    font-weight: bold;
    border-bottom: 1px solid #ccc;
    margin-top: 2em;
    margin-bottom: 0.8em;
}

.gloss-entry {
    font-size: 0.85em;
    margin: 0.4em 0;
    color: #333;
}

.gloss-word { font-weight: bold; margin-right: 0.3em; }
.gloss-reading { color: #666; margin-right: 0.3em; }
.gloss-en { }
.gloss-grammar { color: #888; font-style: italic; }

.grammar-entry {
    font-size: 0.85em;
    margin: 0.4em 0;
}

.grammar-name { font-weight: bold; }
```

### 6.3 EPUB Construction

```python
from ebooklib import epub

def build_epub(episodes: list[ReaderEpisode],
                stage: int,
                series_title: str) -> bytes:
    
    book = epub.EpubBook()
    book.set_title(f"{series_title} — Stage {stage}")
    book.set_language("ja")
    
    css_item = epub.EpubItem(
        file_name="style/michi.css",
        media_type="text/css",
        content=EPUB_CSS
    )
    book.add_item(css_item)
    
    chapters = []
    for ep in episodes:
        chapter_html = render_chapter_html(ep.annotated)
        
        ch = epub.EpubHtml(
            title=ep.outline["title"],
            file_name=f"{ep.id}.xhtml",
            lang="ja"
        )
        ch.content = f"""<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{ep.outline["title"]}</title>
  <link rel="stylesheet" href="../style/michi.css"/>
</head>
<body>
  <h2 class="episode-title">{ep.outline["title"]}</h2>
  {chapter_html}
</body>
</html>"""
        ch.add_item(css_item)
        book.add_item(ch)
        chapters.append(ch)
    
    book.toc = chapters
    book.spine = ["nav"] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    buf = io.BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()
```

**Output:** one EPUB per stage, containing all episodes for that stage as
chapters. Alternatively one EPUB per arc (8–15 episodes) for more manageable
file sizes.

---

## Phase 7 — HTML Transcript Export

Self-contained HTML file. Embeds the timestamps JSON and a minimal audio player
with word-level highlighting. MP3 file is referenced by filename (same directory).
No server required — open in any browser.

### 7.1 Transcript Rendering

```python
def build_transcript_html(audio_package: AudioPackage,
                           annotated_script: list[AnnotatedTurn],
                           episode_id: str,
                           episode_title: str) -> str:
    
    # Build word spans with IDs linked to timestamps
    word_spans = []
    for ts in audio_package.timestamps:
        word_id = f"w{len(word_spans)}"
        
        # Find annotation for this word
        token = find_token(ts["word"], annotated_script)
        
        classes = ["word"]
        data_attrs = [
            f'id="{word_id}"',
            f'data-start="{ts["start_ms"]}"',
            f'data-end="{ts["end_ms"]}"',
            f'data-char="{ts["character"]}"'
        ]
        
        if token:
            classes.append(f"status-{token.status}")
            if token.gloss:
                data_attrs.append(f'data-gloss="{token.gloss.en}"')
            if token.furigana:
                data_attrs.append(f'data-reading="{token.furigana}"')
        
        word_spans.append(
            f'<span {" ".join(data_attrs)} class="{" ".join(classes)}">'
            f'{ts["word"]}</span>'
        )
    
    timestamps_json = json.dumps(audio_package.timestamps)
    
    return TRANSCRIPT_TEMPLATE.format(
        title=episode_title,
        audio_file=f"{episode_id}.mp3",
        word_spans="".join(word_spans),
        timestamps_json=timestamps_json
    )
```

### 7.2 HTML Template

```html
<!-- TRANSCRIPT_TEMPLATE -->
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Hiragino Kaku Gothic Pro", "Noto Sans JP", sans-serif;
    max-width: 700px; margin: 0 auto; padding: 16px;
    background: #fafafa; color: #222;
  }}
  .player {{
    position: sticky; top: 0; background: #fafafa;
    padding: 12px 0; border-bottom: 1px solid #e0e0e0;
    margin-bottom: 20px;
  }}
  audio {{ width: 100%; }}
  .transcript {{ line-height: 2.2; font-size: 1.1em; }}
  .word {{
    display: inline-block;
    padding: 1px 0;
    border-radius: 2px;
    cursor: pointer;
    transition: background 0.08s;
    position: relative;
  }}
  .word.active {{ background: #ffe066; }}
  .word.status-new {{ border-bottom: 2px dotted #e67e22; }}
  .word.status-zone {{ border-bottom: 1px dotted #3498db; }}
  
  /* Furigana on hover */
  .word[data-reading]:hover::before {{
    content: attr(data-reading);
    position: absolute;
    top: -1.4em; left: 50%;
    transform: translateX(-50%);
    font-size: 0.6em; color: #888;
    white-space: nowrap;
    pointer-events: none;
  }}
  
  /* Gloss on hover */
  .word[data-gloss]:hover::after {{
    content: attr(data-gloss);
    position: absolute;
    bottom: 120%; left: 50%;
    transform: translateX(-50%);
    background: #2c3e50; color: #fff;
    padding: 3px 8px; border-radius: 4px;
    font-size: 0.75em; white-space: nowrap;
    z-index: 100; pointer-events: none;
  }}
  
  .char-label {{
    display: block;
    font-size: 0.75em; color: #888;
    margin-top: 0.8em; margin-bottom: 0.1em;
  }}
</style>
</head>
<body>

<div class="player">
  <strong>{title}</strong>
  <audio id="audio" controls preload="metadata" src="{audio_file}"></audio>
</div>

<div id="transcript" class="transcript">
  {word_spans}
</div>

<script>
const words = {timestamps_json};
const audio = document.getElementById('audio');
let activeId = null;

function msToSec(ms) {{ return ms / 1000; }}

audio.addEventListener('timeupdate', () => {{
  const ms = audio.currentTime * 1000;
  
  // Find current word by linear scan
  // (small enough dataset that binary search is unnecessary)
  let found = null;
  for (const w of words) {{
    if (ms >= w.start_ms && ms <= w.end_ms) {{
      found = 'w' + words.indexOf(w);
      break;
    }}
  }}
  
  if (found !== activeId) {{
    if (activeId) {{
      document.getElementById(activeId)?.classList.remove('active');
    }}
    if (found) {{
      const el = document.getElementById(found);
      if (el) {{
        el.classList.add('active');
        el.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
      }}
    }}
    activeId = found;
  }}
}});

// Click word to seek
document.querySelectorAll('.word[data-start]').forEach((el, i) => {{
  el.addEventListener('click', () => {{
    const w = words[i];
    if (w) {{
      audio.currentTime = msToSec(w.start_ms);
      audio.play();
    }}
  }});
}});
</script>
</body>
</html>
```

---

## Phase 8 — Orchestrator

The top-level runner. Generates a batch of episodes for a given stage and arc,
producing all output files.

### 8.1 Episode Output Structure

```
outputs/
  stage1/
    readers/
      arc_daily_life/
        ep_001.epub          # individual episode EPUB (optional)
      stage1_daily_life.epub # combined arc EPUB
    audio/
      arc_daily_life/
        ep_001.mp3
        ep_001_transcript.html
        ep_001_meta.json
```

### 8.2 Meta JSON (per episode)

```json
{
  "episode_id": "ep_001",
  "stage": 1,
  "arc": "daily_life",
  "situation": "コンビニで何かを買おうとしている",
  "generated_at": "2025-03-29T00:00:00",
  "content_type": "audio",
  "validation": {
    "vocab_violation_rate": 0.003,
    "grammar_violations": [],
    "comprehension_estimate": 0.997,
    "attempts_needed": 1
  },
  "ledger_delta": {
    "遠慮する": {"status_before": null, "status_after": "new", "count": 1},
    "慌てる": {"status_before": null, "status_after": "new", "count": 1}
  },
  "new_words_introduced": ["遠慮する", "慌てる"],
  "zone_words_reinforced": ["心配する", "急ぐ"],
  "audio_duration_ms": 94200,
  "total_turns": 10,
  "total_mora": 847
}
```

### 8.3 Batch Generation

```python
def generate_batch(stage: int, arc: str, n_episodes: int,
                    content_type: str) -> None:
    ledger = VocabLedger()
    ledger.load()
    
    stage_config = load_stage_config(stage)
    characters = load_characters(stage)
    
    for i in range(n_episodes):
        print(f"Generating episode {i+1}/{n_episodes}...")
        
        try:
            if content_type == "reader":
                ep = generate_reader_episode(stage, arc, ledger)
                epub_bytes = build_epub([ep], stage, SERIES_TITLE)
                write_output(epub_bytes, stage, arc, ep.id, "epub")
                
            elif content_type == "audio":
                ep = generate_audio_episode(stage, arc, ledger)
                audio_pkg = build_episode_audio(ep.script, stage_config, characters)
                html = build_transcript_html(audio_pkg, ep.annotated_script,
                                              ep.id, ep.title)
                write_output(audio_pkg.mp3, stage, arc, ep.id, "mp3")
                write_output(html.encode(), stage, arc, ep.id, "html")
            
            write_meta(ep.meta, stage, arc, ep.id)
            
        except GenerationFailure as e:
            print(f"  FAILED after 3 attempts: {e}")
            continue
    
    # Build combined arc EPUB from all reader episodes
    if content_type == "reader":
        all_eps = load_arc_episodes(stage, arc)
        arc_epub = build_epub(all_eps, stage, SERIES_TITLE)
        write_arc_epub(arc_epub, stage, arc)
    
    ledger.save()
    print(f"Done. Ledger saved.")
```

### 8.4 CLI

```bash
# Generate 10 reader episodes for Stage 1, daily life arc
python orchestrator.py --stage 1 --arc daily_life --type reader --n 10

# Generate 10 audio episodes for Stage 1, daily life arc
python orchestrator.py --stage 1 --arc daily_life --type audio --n 10

# Generate both types together (interleaved ledger updates)
python orchestrator.py --stage 1 --arc daily_life --n 10

# Check ledger status
python orchestrator.py --status

# Validate an existing episode
python orchestrator.py --validate outputs/stage1/audio/arc_daily_life/ep_001.mp3
```

---

## Phase Summary

| Phase | What it does | Key dependencies |
|---|---|---|
| 0 | Environment, config, character cards | Python, AivisSpeech, Claude API key |
| 1 | Vocabulary ledger (state management) | jamdict, stage_vocab lists |
| 2 | Rule engine (vocab/grammar/complexity) | fugashi + UniDic, grammar_patterns.json |
| 3 | Annotation (furigana, glosses, grammar tags) | fugashi, jamdict |
| 4 | Content generation (outline → prose → validate) | Claude API, Phase 1–2–3 |
| 5 | Audio synthesis + forced alignment | AivisSpeech local API, stable-whisper, pydub |
| 6 | EPUB export | ebooklib, Phase 3 output |
| 7 | HTML transcript export | Phase 5 timestamps + Phase 3 annotations |
| 8 | Orchestrator + CLI | All phases |

**Recommended build order:** 0 → 1 → 2 → 3 → 6 (test reader pipeline end-to-end
with a hardcoded story) → 4 (add generation) → 5 → 7 → 8

Testing the annotation and EPUB export on manually written Japanese before
adding LLM generation catches the majority of pipeline bugs with no API cost.

---

## Known Constraints and Failure Modes

**AivisSpeech timing:** The API does not return per-mora timestamps. Timing
is derived entirely from stable-ts forced alignment post-synthesis. On clean
synthesized audio, accuracy is 20–50ms per word. This is sufficient for
transcript sync but not for phoneme-level analysis.

**Vocabulary boundary cases:** MeCab with UniDic tokenizes some compounds
differently from how they appear in JLPT vocabulary lists. For example,
「大丈夫」 may tokenize as two morphemes. The ledger uses UniDic lemma forms;
the stage vocab lists must be pre-processed into the same lemma form space.
This is a one-time normalization step done when building stage_vocab lists.

**LLM vocab leakage:** Even with correction prompts, Claude occasionally
introduces low-frequency advanced vocabulary through proper noun usage, onomatopoeia,
or colloquial contractions. The rule engine catches these, but 1–3 correction
rounds may be needed per episode at Stage 1–2. At Stage 4+, this rate drops
significantly as the permitted vocabulary space expands.

**stable-ts Japanese alignment:** The `base` Whisper model's Japanese alignment
quality is good on synthesized audio but may struggle with very slow speech
(Stage 1 speed_scale 0.45). If timestamp accuracy is poor at Stage 1, switch
to `small` model or increase speed_scale to 0.55 minimum.

**AivisSpeech concurrent requests:** The engine is designed for single-user
desktop use and is not optimized for concurrent requests. Generate turns
sequentially, not in parallel.
