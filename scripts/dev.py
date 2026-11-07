"""Local development workspace. All mutable state stays inside .local/."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
API = ROOT / "apps/courseware-api"
WEB = ROOT / "apps/courseware-web"


def run(command, cwd=ROOT, env=None):
    subprocess.run(command, cwd=cwd, env=env, check=True)


def environment():
    path = LOCAL / "settings.json"
    if not path.exists():
        raise SystemExit("请先运行 python3 scripts/dev.py setup")
    return json.loads(path.read_text()) | os.environ


def database():
    if not shutil.which("initdb") or not shutil.which("pg_ctl"):
        raise SystemExit("本地启动需要 PostgreSQL（initdb / pg_ctl 在 PATH 中），或使用 deploy/compose.yml")
    directory = LOCAL / "postgres"
    if not directory.exists():
        run(["initdb", "-D", str(directory), "-A", "trust", "--no-locale", "-E", "UTF8", "-U", "courseware"])
    status = subprocess.run(["pg_ctl", "-D", str(directory), "status"], capture_output=True)
    if status.returncode:
        run(["pg_ctl", "-D", str(directory), "-l", str(LOCAL / "postgres.log"),
             "-o", "-p 55438 -h 127.0.0.1 -k /tmp", "start"])
    for name in ["courseware", "courseware_test"]:
        found = subprocess.check_output(["psql", "-h", "127.0.0.1", "-p", "55438", "-U", "courseware",
                                         "-d", "postgres", "-Atc", f"SELECT 1 FROM pg_database WHERE datname='{name}'"], text=True)
        if found.strip() != "1":
            run(["createdb", "-h", "127.0.0.1", "-p", "55438", "-U", "courseware", name])


def setup():
    LOCAL.mkdir(exist_ok=True)
    settings_path = LOCAL / "settings.json"
    if not settings_path.exists():
        settings_path.write_text(json.dumps({
            "CW_DATABASE_URL": "postgresql+psycopg://courseware@127.0.0.1:55438/courseware",
            "CW_SECRET_KEY": secrets.token_urlsafe(48), "CW_PUBLIC_ORIGIN": "http://127.0.0.1:8814",
            "CW_STORAGE_PATH": str(LOCAL / "storage"), "CW_SECURE_COOKIES": "false",
        }, indent=2) + "\n")
        settings_path.chmod(0o600)
    (LOCAL / "storage/releases").mkdir(parents=True, exist_ok=True)
    database()
    run(["uv", "sync", "--frozen"], API)
    run(["npm", "ci"], WEB)
    env = environment()
    run(["uv", "run", "alembic", "upgrade", "head"], API, env)
    credentials = LOCAL / "admin.json"
    if not credentials.exists():
        credentials.write_text(json.dumps({"username": "admin", "password": secrets.token_urlsafe(20)}, indent=2) + "\n")
        credentials.chmod(0o600)
    saved = json.loads(credentials.read_text())
    run(["uv", "run", "courseware", "create-admin", saved["username"], "--if-not-exists"], API,
        env | {"CW_ADMIN_PASSWORD": saved["password"]})
    run(["uv", "run", "courseware", "import-local", "../courseware-demo", "--username", saved["username"], "--list"], API, env)
    print("开发环境已准备。运行 python3 scripts/dev.py start，然后打开 http://127.0.0.1:8814")
    print("本地管理员凭据保存在 .local/admin.json（仅本机可读，不提交 Git）。")


def start():
    database()
    env = environment()
    commands = [
        (["uv", "run", "uvicorn", "courseware.main:app", "--host", "127.0.0.1", "--port", "8008"], API),
        (["uv", "run", "courseware", "worker"], API),
        (["npm", "run", "dev"], WEB),
    ]
    children = []
    try:
        for command, cwd in commands:
            children.append(subprocess.Popen(command, cwd=cwd, env=env))
        print(f"Courseware: {env['CW_PUBLIC_ORIGIN']}  (Ctrl+C 停止应用；数据库保持运行)", flush=True)
        while all(child.poll() is None for child in children):
            try:
                children[0].wait(timeout=1)
            except subprocess.TimeoutExpired:
                continue
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["setup", "start", "test", "types", "stop-db", "credentials"])
    args = parser.parse_args()
    if args.command == "setup":
        setup()
    elif args.command == "start":
        start()
    elif args.command == "test":
        env = environment() | {"CW_DATABASE_URL": "postgresql+psycopg://courseware@127.0.0.1:55438/courseware_test"}
        run(["uv", "run", "pytest", "-q"], API, env)
        run(["npm", "run", "build"], WEB)
    elif args.command == "types":
        run(["uv", "run", "courseware", "export-openapi", "openapi.json"], API, environment())
        run(["npm", "run", "types"], WEB)
    elif args.command == "stop-db":
        run(["pg_ctl", "-D", str(LOCAL / "postgres"), "stop"])
    else:
        print((LOCAL / "admin.json").read_text())


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
