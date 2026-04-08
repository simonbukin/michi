# Michi Parallel Content System

Generates graded reader EPUBs and audio dialogues (MP3s + synchronized HTML transcripts) to accompany the Michi textbook.

## Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download UniDic dictionary (required for MeCab tokenization)
python -m unidic download

# Copy environment template and add your API key
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY=sk-...

# AivisSpeech (required for audio generation only)
# Install from https://aivis-project.com and start the server on port 10101
```

## Usage

```bash
# Seed vocabulary ledger from textbook
python -m ledger.seed_from_textbook

# Generate content
python orchestrator.py --stage 1 --arc daily_life --type reader --n 5
python orchestrator.py --stage 1 --arc daily_life --type audio --n 5

# Check ledger status
python orchestrator.py --status
```

See `SPEC.md` for full technical specification.
