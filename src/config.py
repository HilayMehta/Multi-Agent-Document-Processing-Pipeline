"""Central configuration — all values env-overridable."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Models ────────────────────────────────────────────────────────────────────
MODEL_CLASSIFY: str = os.getenv("MODEL_CLASSIFY", "gpt-4o-mini")
MODEL_EXTRACT: str = os.getenv("MODEL_EXTRACT", "gpt-4o")
MODEL_TAG: str = os.getenv("MODEL_TAG", "gpt-4o")
MODEL_SUMMARY: str = os.getenv("MODEL_SUMMARY", "gpt-4o")
# Embedding model for the eval's semantic summary-similarity metric (pin for reproducibility).
MODEL_EMBED: str = os.getenv("MODEL_EMBED", "text-embedding-3-small")

# ── Token limits ──────────────────────────────────────────────────────────────
MAX_TOKENS_CLASSIFY: int = 512
MAX_TOKENS_EXTRACT: int = 4096
MAX_TOKENS_TAG: int = 512
MAX_TOKENS_SUMMARY: int = 512

# ── Pipeline behaviour ────────────────────────────────────────────────────────
CLASSIFY_CONFIDENCE_THRESHOLD: float = float(
    os.getenv("CLASSIFY_CONFIDENCE_THRESHOLD", "0.7")
)
MAX_RETRIES_PER_STAGE: int = int(os.getenv("MAX_RETRIES_PER_STAGE", "2"))

# Characters of raw_text sent to classifier (type announces itself early)
CLASSIFY_WINDOW: int = 2000

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).parent.parent
OUTPUT_DIR: Path = ROOT_DIR / "output"
DATA_DIR: Path = ROOT_DIR / "data"
SAMPLES_DIR: Path = DATA_DIR / "samples"
GROUND_TRUTH_PATH: Path = DATA_DIR / "ground_truth.json"

OUTPUT_DIR.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
