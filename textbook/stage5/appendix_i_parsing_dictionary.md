# Appendix I — Dictionary Use, Parsing, and Reading Ambiguity

This appendix is the meta-skill toolkit. Stage 5's Chapter 12 (Building Reading Stamina) covered when to look up versus skip and how to manage fatigue. This appendix covers the complementary problem: **once you decide to look something up or to parse a difficult sentence, how do you actually do it well?** And: **when grammar and vocabulary are both known but the sentence is still opaque, what is going on?**

The skills here are the difference between a learner who has finished N1 grammar and a reader who can actually finish a Japanese novel. Without them, reading remains effortful even when nothing technically unknown is present. With them, you can recover from any sentence that initially defeats you.

---

## I.1 Choosing a Dictionary

There is no single best Japanese dictionary. Different tools serve different purposes, and a fluent reader uses several depending on context.

### Bilingual J-E dictionaries (definitions in English)

| Tool | Strengths | Weaknesses | Best for |
|------|-----------|------------|----------|
| **Jisho.org** | Free, fast, JMdict-based, kanji lookup by radical and handwriting, conjugation tables. | Definitions can be terse; no usage examples by default. | Quick lookups, kanji decomposition, beginner-to-intermediate use. |
| **Yomichan / Yomitan (browser extension)** | Hover-over instant lookup on any web page; supports multiple dictionary backends; AnkiConnect integration. | Initial setup required; relies on dictionaries you install. | Heavy reading on the web; building Anki cards while you read. |
| **Imiwa? (iOS)** | Offline, well-organized, includes example sentences, kanji-by-radical search. | iOS only; UI is dense. | Mobile lookups when offline. |
| **Takoboto (Android)** | Offline, JMdict-based, fast. | Android only. | Mobile lookups when offline. |

**A note on JMdict.** Many free dictionaries (Jisho, Imiwa, Takoboto, Yomichan default) draw from the same underlying database — JMdict, an open-source Japanese-English dictionary maintained for decades. This means their definitions are similar, sometimes identical. The differences are interface and speed, not content.

### Monolingual J-J dictionaries (definitions in Japanese)

At Stage 5+ you should be transitioning to monolingual dictionaries when the J-E definition feels insufficient.

| Tool | Strengths | Weaknesses | Best for |
|------|-----------|------------|----------|
| **大辞林 / 大辞泉** | Authoritative, comprehensive, distinguishes nuanced senses. | Heavier definitions; requires N3-N2 reading ability. | Serious reading; resolving subtle meaning differences. |
| **三省堂国語辞典** (三国, さんこく) | Modern, descriptive (records living usage including slang), concise. | Less historical depth. | Contemporary written and spoken Japanese. |
| **新明解国語辞典** (新解さん) | Famous for opinionated, almost literary definitions. | Stylized; not always neutral. | Reading for cultural texture; understanding what a word *evokes*. |
| **Weblio** (online) | Aggregates multiple dictionaries; free. | Cluttered interface. | Quick access to monolingual definitions on the web. |
| **Goo辞書** (online) | Free, clean interface, good for everyday lookups. | Less depth than print dictionaries. | Daily reading checks. |

When a J-E definition gives you "to express; to indicate; to show" for a single Japanese verb, a monolingual dictionary will explain the difference between the senses: which contexts each takes, which collocations, which register. This is information J-E dictionaries cannot easily encode.

### Specialized dictionaries

- **类语辞典** (類語辞典, thesaurus): essential for understanding which of several near-synonyms is appropriate in a given context. Online options: Weblio's 類語辞典 module.
- **慣用句辞典 / 四字熟語辞典**: idiom and four-character compound dictionaries are useful when an expression seems to be more than the sum of its parts.
- **古語辞典**: classical Japanese dictionaries. At Stage 5, you only need these for serious literary reading, not everyday text.
- **NHKアクセント辞典 / 新明解日本語アクセント辞典**: for pitch accent.

### When to use which

| Situation | Reach for |
|-----------|-----------|
| Quick lookup while reading | Jisho or Yomichan |
| Building an Anki card | Yomichan + monolingual dictionary export |
| Resolving subtle nuance between synonyms | 類語辞典 + monolingual definition |
| Understanding an unfamiliar idiom | 慣用句辞典 or Goo辞書 |
| Checking pitch accent | NHK辞典 (or Weblio's 発音 mode) |
| Studying for the JLPT | Jisho / Imiwa for speed; monolingual for depth |

The fluent-reader habit: J-E for first-pass identification, monolingual when you actually want to understand. Skipping the monolingual step keeps you in a comfortable but limiting middle ground.

---

## I.2 Parsing Sentences That Defeat You

Sometimes you know every word and every grammar pattern in a sentence, and you still cannot parse it. This is not a failure of knowledge. It is a failure of *strategy*. Japanese sentence structure rewards specific habits that English-trained readers often lack.

### Step 1: Find the main verb and work backwards

Japanese is head-final: the main predicate (verb, copula, or final adjective) is at the end of the sentence. **Find it first.** Everything before it modifies it, scopes over it, or is a topic/subject for it.

> 政府が長年にわたり実施してきた経済対策は、若者の就職難という根本的な問題を解決するには至っていない。

Main verb: **至っていない** (has not reached). Now you have an anchor.

### Step 2: Identify the topic and the subject

Look for は (topic), が (subject), and any compound topic markers (について, に関しては, etc.). These tell you *what the sentence is about* and *what is doing the action*.

In the example above:
- Topic (after は): 政府が長年にわたり実施してきた経済対策 — *the economic measures the government has implemented over many years*
- Object: 問題を — *(the) problem (object)*
- Predicate: 解決するには至っていない — *has not reached the point of solving*

### Step 3: Bracket the noun-modifying clauses

Japanese stacks relative clauses and modifiers before the noun without commas. When a sentence feels long, the trick is to find the noun being modified and mentally bracket the modifier:

> [政府が長年にわたり実施してきた] 経済対策

The bracketed clause modifies 経済対策. Treat the whole bracket as one unit when parsing the rest of the sentence.

Rule of thumb: if you see a verb followed directly by a noun (no か, the verb is in plain or polite form), the verb is modifying the noun.

### Step 4: Find the implicit subject

Japanese routinely drops subjects. When a sentence starts with a verb or adjective, ask: *whose action is this?* The answer is usually the topic of the previous sentence, the speaker, or a generic "people / one."

> 雨が降ってきた。傘を持ってこなかった。
> *It started raining. (I/we) didn't bring an umbrella.*

The second sentence has no overt subject. Context fills it in.

This is called **zero anaphora**. It is one of the most common reasons English readers stall on Japanese: the subject is grammatically absent but pragmatically obvious. Train yourself to ask "who?" automatically when a verb appears without an explicit subject.

### Step 5: Decompose particle stacks

Compound particles (に対して, に関して, について, によって, に基づいて, をめぐって, をはじめ, をとおして, etc.) function as units. When you see a particle followed by another particle or relational noun, treat the cluster as a single grammatical unit. Looking up the cluster as a unit is faster than parsing each piece.

### Step 6: When all else fails — rewrite in modern colloquial form

If a sentence uses formal, classical, or written-register grammar, mentally rewrite it in modern conversational form:

> 必要なくしては成功はあり得ない。
> → 必要がなければ、成功することはできない。
> *Without need(?), success is impossible.*

The second version is awkward but parseable. Once you know what the sentence means, you can re-engage with the original to feel the formal register.

---

## I.3 Handling Ambiguity

Some Japanese sentences are genuinely ambiguous. Knowing when ambiguity is real (and how it is usually resolved) is itself a comprehension skill.

### Subject ambiguity

> 田中さんが山田さんに本を貸した。
> *Tanaka lent a book to Yamada.*

Clear. But:

> 山田さんに本を貸した。
> *(I/Tanaka/someone) lent a book to Yamada.*

Without context, the lender is unspecified. Look at the **previous sentence** to recover it.

### Modifier scope

> 古い学校の先生
> Possible readings: *the old school's teacher* OR *the teacher of the old school* OR *the old teacher of the school*.

Native readers default to the most natural reading by context. When you cannot decide, prefer the reading that fits the surrounding discourse.

### Tense ambiguity

Plain past forms (～た) can mean past completion, recent perfect, or even — in certain contexts — present habitual or future hypothetical:

> 思った通りだった。 *(It) was as (I) thought.*
> 帰ったらすぐ寝ます。 *When (I) get home, (I'll) sleep immediately.*

The second 帰った is non-past, despite the form. This is a feature of the Japanese tense system: ～た encodes completion relative to a reference point, not absolute past.

### に versus で

For locations, に marks where something exists or is going; で marks where an action takes place. Most of the time. But:

> 公園に座る。 *(I) sit (down) in the park.* (movement into a sitting position)
> 公園で座る。 *(I) sit in the park.* (sitting is the activity, in the park as venue)

The difference is subtle. When parsing, ask whether the verb describes a location of being (に) or an activity (で).

### は versus が in subordinate clauses

The default is that が appears in subordinate clauses, は in main clauses. When は appears in a subordinate clause, it carries contrastive force:

> 私が買った本 — *the book I bought* (neutral)
> 私は買った本 — *the book I bought (as opposed to others)*

The second is grammatical only if a contrast is implied.

---

## I.4 Strategic Skipping: When NOT to Look Up

Stage 5 Chapter 12 covered this strategically. Here is the operational test:

| Situation | Action |
|-----------|--------|
| You can guess from context within ±20% accuracy | Skip and continue |
| The unknown word recurs three or more times in the passage | Look up |
| The word is in a key sentence (topic, conclusion, or main argument) | Look up |
| The word is in a list, parenthetical, or example | Skip |
| You feel the urge to look up out of perfectionism | Skip |
| Looking up will break a flow you've established | Skip and note for later |

For extensive reading at Stage 5+, your skip rate should be roughly 80-95%. If you are looking up more than one word per page, you are reading material above your level — not as extensive reading but as intensive study, which is a different activity.

---

## I.5 Common Parse Failures and Their Fixes

This table catalogs the most common ways an advanced learner gets stuck on a sentence whose pieces they technically know.

| Failure | Symptom | Fix |
|---------|---------|-----|
| Lost the main verb | Sentence feels endless; can't find the predicate | Skip to the period, work backwards |
| Missed a relative clause boundary | Unable to identify what modifies what | Look for verb-then-noun patterns; bracket modifying clauses |
| Implicit subject confusion | Action feels disconnected | Ask "whose action?"; recover from prior context |
| Compound particle treated as separate words | Particles seem to make no sense | Treat に対して, について, etc. as units |
| Classical residue treated as modern | Form looks impossible | Rewrite mentally in modern colloquial |
| Onomatopoeia not recognized | Adverbial section seems untethered | Identify reduplicative or と-bound forms; look up the onomatopoeia |
| Topic chain broken | Sentence's "about" feels arbitrary | Recover topic from prior sentence's は or implicit context |
| Embedded quotation missed | Can't find the speaker | Look for と思う/と言う/とした and trace backward |
| Discourse marker overlooked | Logical flow feels random | Note けれども, にもかかわらず, それでも, 一方で as pivots |
| Negative scope misread | Meaning is reversed | Check whether negation attaches to verb, modal, or whole clause |

---

## I.6 Building the Habit

These skills become automatic only with deliberate practice. A useful drill:

**Take an N1 reading passage. Time yourself reading it, then re-read the same passage and explicitly identify, for each sentence:**

1. The main verb / predicate
2. The topic (overt or implicit)
3. The subject of the main verb (overt or implicit)
4. Any noun-modifying clauses (boundaries marked)
5. Any compound particles (treated as units)
6. Any classical or formal-register elements

After ten passages of this drill, the steps will collapse into a single fluid pass. Until they do, the explicit version is faster than confused re-reading.

The promise of advanced Japanese reading is that, eventually, parsing becomes invisible. You read a sentence and the meaning arrives. The methods in this appendix are the scaffolding that supports that invisibility — useful early, optional later, and crucial when a hard sentence breaks your fluency and you need to recover.
