# 道 (michi)

A structured Japanese textbook and reference suite, from N5 to beyond N1.

> **Disclaimer:** All content in this project is AI-generated via Claude Opus 4.6. It has not been reviewed or verified by professional Japanese language instructors. Use at your own discretion and cross-reference with trusted resources.

## Books

**Textbook** — The core curriculum. Six stages of grammar, vocabulary, and kanji instruction mapped to JLPT levels N5 through N1.

**Immersion Guide** — A companion methodology guide. Covers what to consume, when to start immersing, and how to build effective habits at each stage.

**Colloquial Patterns** — A pattern dictionary for casual Japanese. Maps spoken and written contractions, slang, and informal grammar back to their textbook forms.

**Reading Companions** — Vocabulary and grammar maps for reading real Japanese works. Each companion covers one volume of a manga or novel, listing the words and grammar you need chapter by chapter.

## Development

Requires [mdbook](https://github.com/rust-lang/mdBook) and Python 3.

```sh
# Build all books
./build.sh

# Serve individual books locally
make serve              # textbook on :3000
make immersion-serve    # immersion on :3001
make colloquial-serve   # colloquial on :3002
make companions-serve   # companions on :3003
```

## Deployment

Deployed via Vercel. A single `build.sh` builds all four books into `dist/`, which Vercel serves as a static site.
