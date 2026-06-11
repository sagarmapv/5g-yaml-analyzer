import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1])).resolve()

YAML_DIR = PROJECT_ROOT / "Yaml-Files" / "5GC_APIs"
CONTENT_DIR = PROJECT_ROOT / "content"
SPEC_PDF_DIR = YAML_DIR
PARSED_JSON_DIR = PROJECT_ROOT / "Parsed-JSON"
BANK_DIR = PROJECT_ROOT / "Bank"
INDEX_JSON = PROJECT_ROOT / "index.json"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BUILD_STATUS_FILE = PROJECT_ROOT / ".build-status.json"

DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "127.0.0.1")

HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "options", "head", "trace"})
