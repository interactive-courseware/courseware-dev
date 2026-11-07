"""Exercise the production Nginx/X-Accel flow on loopback with a temporary TLS certificate."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import httpx

root = Path(__file__).resolve().parents[1]
work = root / ".local/gateway"
work.mkdir(parents=True, exist_ok=True)
if not shutil.which("nginx") or not shutil.which("openssl"):
    raise SystemExit("This optional native check requires nginx and openssl.")
if not (root / "apps/courseware-web/dist/index.html").exists():
    raise SystemExit("Build courseware-web first.")
subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                "-subj", "/CN=localhost", "-keyout", str(work / "privkey.pem"),
                "-out", str(work / "fullchain.pem")], check=True, capture_output=True)
(work / "privkey.pem").chmod(0o600)
config = (root / "deploy/nginx.conf").read_text()
config = config.replace("listen 80;", "listen 127.0.0.1:58088;")
config = config.replace("listen 443 ssl;", "listen 127.0.0.1:58443 ssl;")
config = config.replace("https://$host$request_uri", "https://$host:58443$request_uri")
config = config.replace("/etc/nginx/tls", str(work)).replace("/usr/share/nginx/html", str(root / "apps/courseware-web/dist"))
config = config.replace("/srv/courseware/releases/", str(root / ".local/storage/releases") + "/")
config = config.replace("http://api:8000", "http://127.0.0.1:58011")
nginx = shutil.which("nginx")
prefix = Path(nginx).resolve().parents[1]
mime_candidates = [prefix / "conf/mime.types", Path("/opt/homebrew/etc/nginx/mime.types"), Path("/etc/nginx/mime.types")]
mime = next((p for p in mime_candidates if p.exists()), None)
if not mime:
    raise SystemExit("Cannot locate Nginx mime.types.")
config = (f'pid "{work}/nginx.pid";\nerror_log "{work}/nginx.log";\nevents {{}}\nhttp {{\n'
          f'include "{mime}";\naccess_log off;\n' + config + '\n}\n')
conf = work / "nginx.conf"
conf.write_text(config)
subprocess.run([nginx, "-p", str(work), "-c", str(conf), "-t"], check=True)
env = os.environ | json.loads((root / ".local/settings.json").read_text()) | {
    "CW_PUBLIC_ORIGIN": "https://localhost:58443", "CW_SECURE_COOKIES": "true", "CW_X_ACCEL": "true",
}
with (work / "api.log").open("w") as log:
    api = subprocess.Popen(["uv", "run", "uvicorn", "courseware.main:app", "--host", "127.0.0.1", "--port", "58011"],
                           cwd=root / "apps/courseware-api", env=env, stdout=log, stderr=log)
    started = False
    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:58011/health/live").status_code == 200:
                    break
            except httpx.ConnectError:
                pass
            time.sleep(.1)
        else:
            raise RuntimeError("Gateway test API did not start")
        subprocess.run([nginx, "-p", str(work), "-c", str(conf)], check=True)
        started = True
        with httpx.Client(base_url="https://localhost:58443", verify=False) as client:
            portal = client.get("/login")
            assert portal.status_code == 200
            assert portal.headers["strict-transport-security"] == "max-age=31536000"
            assert portal.headers["x-content-type-options"] == "nosniff"
            assert client.get("/api/v1/courses").status_code == 401
            token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            creds = json.loads((root / ".local/admin.json").read_text())
            login = client.post("/api/v1/auth/login", json=creds,
                                headers={"Origin":env["CW_PUBLIC_ORIGIN"], "X-CSRF-Token":token})
            assert login.status_code == 200, login.status_code
            assert "Secure" in login.headers["set-cookie"] and "HttpOnly" in login.headers["set-cookie"]
            course = client.get("/api/v1/courses/courseware-demo").json()
            image = client.get(course["cover"]["url"])
            assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
            assert image.headers["cache-control"] == "private, no-store", image.headers["cache-control"]
            assert client.head(course["cover"]["url"]).status_code == 200
            partial = client.get(course["cover"]["url"], headers={"Range":"bytes=0-9"})
            assert partial.status_code == 206 and len(partial.content) == 10
            raw = f"/_protected/{course['id']}/{course['release_id']}/assets/cover.png"
            assert client.get(raw).status_code == 404
            assert client.get("/api/v1/missing").status_code == 404
            assert client.get("/courses/courseware-demo/missing.html").status_code == 404
            logout = client.post("/api/v1/auth/logout", headers={"Origin":env["CW_PUBLIC_ORIGIN"],
                                                                  "X-CSRF-Token":login.json()["csrf_token"]})
            assert logout.status_code == 204
            assert client.get(course["cover"]["url"]).status_code == 401
        print("Nginx TLS + secure login + X-Accel files + HEAD/Range + internal isolation + logout checks passed.")
    finally:
        if started:
            subprocess.run([nginx, "-p", str(work), "-c", str(conf), "-s", "quit"], check=False)
        api.terminate()
        api.wait(timeout=10)
