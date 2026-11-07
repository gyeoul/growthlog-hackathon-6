"""Contract tests: routing/validation plus the LLM seam, no network needed."""

import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services import llm

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_chat_rejects_empty_messages():
    assert client.post("/api/chat", json={"messages": []}).status_code == 422


def test_chat_returns_completion(monkeypatch):
    async def fake_complete(settings, messages):
        assert messages[-1].content == "hi"
        return "hello"

    monkeypatch.setattr(llm, "complete", fake_complete)
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert res.status_code == 200
    assert res.json() == {"content": "hello", "model": get_settings().llm_model}


def test_chat_maps_llm_failure_to_502(monkeypatch):
    async def boom(settings, messages):
        raise llm.LLMError("down")

    monkeypatch.setattr(llm, "complete", boom)
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert res.status_code == 502
    assert res.json()["detail"] == "down"


def test_stream_emits_deltas_then_done(monkeypatch):
    async def fake_stream(settings, messages):
        for part in ["Hel", "lo"]:
            yield part

    monkeypatch.setattr(llm, "stream", fake_stream)
    with client.stream(
        "POST", "/api/chat/stream", json={"messages": [{"role": "user", "content": "hi"}]}
    ) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        body = "".join(res.iter_text())

    events = [line[6:] for line in body.splitlines() if line.startswith("data: ")]
    assert events == ['{"delta": "Hel"}', '{"delta": "lo"}', "[DONE]"]


def test_stream_reports_llm_error_in_band(monkeypatch):
    async def boom(settings, messages):
        raise llm.LLMError("nope")
        yield  # pragma: no cover

    monkeypatch.setattr(llm, "stream", boom)
    with client.stream(
        "POST", "/api/chat/stream", json={"messages": [{"role": "user", "content": "hi"}]}
    ) as res:
        body = "".join(res.iter_text())
    assert json.loads(body.split("data: ")[1]) == {"error": "nope"}
    assert body.rstrip().endswith("[DONE]")
