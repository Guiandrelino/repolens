import json
from types import SimpleNamespace
from unittest.mock import patch

from app.agents import demo_report, run_agents
from app.repository import DEMO_FILES, Repository


class Message:
    def __init__(self, content=None, calls=None):
        self.content = content
        self.tool_calls = calls

    def model_dump(self, **_):
        if self.tool_calls:
            return {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.function.name, "arguments": c.function.arguments},
                    }
                    for c in self.tool_calls
                ],
            }
        return {"role": "assistant", "content": self.content}


def test_graph_executes_both_agents_with_tools(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "openai_api_key", "fake-test-key")
    repo = Repository(DEMO_FILES, "0" * 40)
    draft = json.dumps(demo_report(repo))
    call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="read_file", arguments=json.dumps({"path": "src/api/users.js"})),
    )
    messages = iter(
        [Message(calls=[call]), Message(content=draft), Message(calls=[call]), Message(content=draft)]
    )
    events = []

    def response(**_):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=next(messages))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50),
        )

    with patch("app.agents.OpenAI") as client:
        client.return_value.chat.completions.create.side_effect = response
        report, metrics = run_agents(repo, "quality", events.append)
        client.return_value.close.assert_called_once()
    assert len(report["findings"]) == 2
    assert metrics["tool_calls"] == 2
    assert metrics["input_tokens"] == 400
    assert any("Analista: read_file" in event for event in events)
    assert any("Revisor:" in event for event in events)
