"""Seed an isolated browser-test database, never the development database."""
import json
import os
from pathlib import Path
import secrets
import subprocess

root = Path(__file__).resolve().parents[1]
directory = root / ".local/e2e"
directory.mkdir(parents=True, exist_ok=True)
found = subprocess.check_output(["psql", "-h", "127.0.0.1", "-p", "55438", "-U", "courseware", "-d", "postgres",
                                 "-Atc", "SELECT 1 FROM pg_database WHERE datname='courseware_e2e'"], text=True)
if found.strip() != "1":
    subprocess.run(["createdb", "-h", "127.0.0.1", "-p", "55438", "-U", "courseware", "courseware_e2e"], check=True)
env = os.environ | json.loads((root / ".local/settings.json").read_text()) | {
    "CW_DATABASE_URL": "postgresql+psycopg://courseware@127.0.0.1:55438/courseware_e2e",
    "CW_STORAGE_PATH": str(directory / "storage"), "CW_PUBLIC_ORIGIN": "http://localhost:58174",
}
credentials = {"username": "manager", "password": secrets.token_urlsafe(24)}
path = directory / "credentials.json"
path.write_text(json.dumps(credentials))
path.chmod(0o600)
api = root / "apps/courseware-api"
subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=api, env=env, check=True)
subprocess.run(["uv", "run", "python", "-c", """
from sqlalchemy import text
from courseware.db import engine
from courseware.models import Base
assert engine().url.database == 'courseware_e2e'
with engine().begin() as conn:
    conn.execute(text('TRUNCATE ' + ', '.join('"' + name + '"' for name in Base.metadata.tables) + ' CASCADE'))
"""], cwd=api, env=env, check=True)
subprocess.run(["uv", "run", "courseware", "create-admin", credentials["username"]], cwd=api,
               env=env | {"CW_ADMIN_PASSWORD": credentials["password"]}, check=True)
subprocess.run(["uv", "run", "courseware", "import-local", "../courseware-demo", "--username", credentials["username"], "--list"],
               cwd=api, env=env, check=True)
