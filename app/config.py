import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")           # local runs only; Cloud Run passes the key as an environment variable

MODEL_PATH = BASE_DIR / "model" / "attrition_model.joblib"
MODEL_CARD_PATH = BASE_DIR / "model" / "model_card.json"
STATIC_DIR = BASE_DIR / "static"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_TIMEOUT_SECONDS = 25

MAX_UPLOAD_BYTES = 1_000_000              # 1 MB CSV
MAX_BATCH_ROWS = 1000

# Cloud Storage bucket mounted as a folder (Cloud Run volume). If the folder does not exist, saving is off.
DATA_DIR = Path(os.getenv("DATA_DIR", "/mnt/data"))


def openai_key():
    return os.getenv("OPENAI_API_KEY", "").strip()
