from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agents import demo_report, validate_findings
from app.main import app
from app.repository import DEMO_FILES, Repository
from app.schemas import AnalysisCreate, ReportDraft
from app.tasks import analyze_repository

URL = "https://github.com/example/project"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b",
        "https://evil.com/a/b",
        "https://github.com@evil.com/a/b",
        "https://github.com/a/b?x=1",
        "https://github.com/a/..",
        "https://github.com/a/b/tree/main",
        "https://github.com:443/a/b",
    ],
)
def test_url_rejects_untrusted_hosts_and_paths(url):
    with pytest.raises(ValidationError):
        AnalysisCreate(repo_url=url)


def test_url_normalizes():
    assert (
        AnalysisCreate(repo_url="https://github.com/user/project.git/").repo_url
        == "https://github.com/user/project"
    )


def test_anonymous_and_csrf(client):
    assert client.get("/analyses").status_code == 401
    assert client.post("/auth/demo", headers={"Origin": "https://evil.com"}).status_code == 403
    assert client.post("/auth/demo", headers={"Origin": "null"}).status_code == 403


def test_full_demo_flow_and_isolation(logged_in):
    with patch("app.main.analyze_repository.delay") as queue:
        response = logged_in.post("/analyses", json={"repo_url": URL})
        assert response.status_code == 202
        analysis_id = response.json()["id"]
        queue.assert_called_once_with(analysis_id)
        assert logged_in.post("/analyses", json={"repo_url": URL}).status_code == 429
    analyze_repository.run(analysis_id)
    report = logged_in.get(f"/analyses/{analysis_id}").json()
    assert report["status"] == "completed"
    assert len(report["findings"]) == 2
    assert report["metrics"]["input_tokens"] == 0
    finding = report["findings"][0]
    endpoint = f"/analyses/{analysis_id}/findings/{finding['id']}"
    assert logged_in.patch(endpoint, json={"resolved": True}).json()["resolved"]
    exported = logged_in.get(f"/analyses/{analysis_id}/export")
    assert exported.status_code == 200
    assert "DEMONSTRAÇÃO" in exported.text
    stream = logged_in.get(f"/analyses/{analysis_id}/events")
    assert "event: done" in stream.text
    assert "Relatório concluído" in stream.text
    # Reentrega não duplica achados.
    analyze_repository.run(analysis_id)
    assert len(logged_in.get(f"/analyses/{analysis_id}").json()["findings"]) == 2
    with TestClient(app, headers={"Origin": "http://localhost:3000"}) as other:
        other.post("/auth/demo")
        assert other.get("/analyses").json() == []
        for path in [
            f"/analyses/{analysis_id}",
            f"/analyses/{analysis_id}/export",
            f"/analyses/{analysis_id}/events",
        ]:
            assert other.get(path).status_code == 404
        assert other.patch(endpoint, json={"resolved": False}).status_code == 404


def test_queue_failure_is_visible(logged_in):
    with patch("app.main.analyze_repository.delay", side_effect=ConnectionError):
        result = logged_in.post("/analyses", json={"repo_url": URL}).json()
        assert result["status"] == "failed"
        assert "Fila indisponível" in result["error"]


def test_evidence_validation_rejects_fabrications():
    repo = Repository(DEMO_FILES, "0" * 40)
    draft = ReportDraft.model_validate(demo_report(repo))
    assert len(validate_findings(draft, repo)["findings"]) == 2
    draft.findings[0].evidence = "inventado"
    draft.findings[1].end_line = 100
    assert validate_findings(draft, repo)["findings"] == []


def test_read_tools_do_not_access_disk():
    repo = Repository(DEMO_FILES, "0" * 40)
    assert "não disponível" in repo.tool("read_file", {"path": "../../.env"})
    assert "2:" in repo.tool("read_file", {"path": "src/api/users.js", "start_line": 2, "end_line": 2})
    assert "src/api/users.js:2" in repo.tool("search_code", {"query": "findById"})
    assert "desconhecida" in repo.tool("shell", {"command": "whoami"})
