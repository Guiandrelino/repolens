"""Smoke test contra Docker Compose em modo demo: py smoke.py."""
import http.cookiejar
import json
import time
import urllib.request

BASE = "http://localhost:8000"
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path, method="GET", body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"Origin": "http://localhost:3000", "Content-Type": "application/json"})
    with opener.open(req, timeout=15) as response:
        raw = response.read().decode()
        return json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else raw


assert request("/health")["mode"] == "demo", "Execute apenas no ambiente demo"
request("/auth/demo", "POST")
analysis = request("/analyses", "POST", {"repo_url": "https://github.com/example/project", "focus": "quality"})
for _ in range(30):
    report = request(f"/analyses/{analysis['id']}")
    if report["status"] in {"completed", "failed"}:
        break
    time.sleep(1)
assert report["status"] == "completed", report
assert len(report["findings"]) == 2
finding = report["findings"][0]
assert request(f"/analyses/{analysis['id']}/findings/{finding['id']}", "PATCH", {"resolved": True})["resolved"]
assert "DEMONSTRAÇÃO" in request(f"/analyses/{analysis['id']}/export")
assert "event: done" in request(f"/analyses/{analysis['id']}/events")
with urllib.request.urlopen("http://localhost:3000", timeout=15) as web:
    assert "RepoLens" in web.read().decode()
print("OK: frontend, sessão, PostgreSQL, Redis, worker, relatório, resolução, exportação e SSE.")
