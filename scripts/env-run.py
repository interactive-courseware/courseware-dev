"""Run a development command with private local settings; never print secret values."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
settings_file = root / ".local/settings.json"
if not settings_file.exists():
    raise SystemExit("Run python3 scripts/dev.py setup first.")
environment = json.loads(settings_file.read_text()) | os.environ
if os.environ.get("CW_TEST_DATABASE_URL"):
    environment["CW_DATABASE_URL"] = os.environ["CW_TEST_DATABASE_URL"]
if len(sys.argv) < 3:
    raise SystemExit("Usage: env-run.py <working-directory> <command> [arguments...]")
result = subprocess.run(sys.argv[2:], cwd=root / sys.argv[1], env=environment)
raise SystemExit(result.returncode)
