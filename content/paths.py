"""Cross-repo path constants for the content generation pipeline."""

from pathlib import Path

# Root of the content pipeline
CONTENT_DIR = Path(__file__).resolve().parent

# Monorepo root
REPO_ROOT = CONTENT_DIR.parent

# Sibling books
TEXTBOOK_DIR = REPO_ROOT / "textbook"
IMMERSION_DIR = REPO_ROOT / "immersion"
COLLOQUIAL_DIR = REPO_ROOT / "colloquial"

# Content pipeline paths
CONFIG_DIR = CONTENT_DIR / "config"
LEDGER_DIR = CONTENT_DIR / "ledger"
OUTPUTS_DIR = CONTENT_DIR / "outputs"

# Ledger state file
VOCAB_LEDGER_PATH = LEDGER_DIR / "vocab_ledger.json"

# Master vocabulary (single source of truth)
MASTER_VOCAB_PATH = REPO_ROOT / "shared" / "vocab" / "master_vocab.json"
