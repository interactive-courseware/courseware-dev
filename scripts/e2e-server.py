import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = os.environ | json.loads((root / ".local/settings.json").read_text()) | {
    "CW_DATABASE_URL": "postgresql+psycopg://courseware@127.0.0.1:55438/courseware_e2e",
    "CW_STORAGE_PATH": str(root / ".local/e2e/storage"),
    "CW_PUBLIC_ORIGIN": "http://localhost:58174",
}
os.chdir(root / "apps/courseware-api")
os.execvpe("uv", ["uv", "run", "uvicorn", "courseware.main:app", "--host", "127.0.0.1", "--port", "58110"], env)
