import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.deps.auth import get_current_user


def _parse_sse_events(body: str) -> list[dict]:
    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


async def _mock_orchestrator_stream(state):
    yield {
        "analyzer": {
            "intent": "Evaluate growth strategy",
            "active_agents": ["visionary", "risk"],
        }
    }
    yield {
        "parallel_agents": {
            "draft_responses": {
                "visionary": {
                    "analysis": "Strong market opportunity",
                    "risks": ["Competition"],
                    "recommendations": ["Focus on niche"],
                    "confidence": 0.85,
                }
            }
        }
    }
    yield {"critic": {"critiques": {"visionary": {"flaws": [], "severity": "low"}}}}
    yield {"synthesizer": {"final_consensus": "Proceed with focused niche strategy."}}


@pytest.mark.asyncio
async def test_boardroom_sse_flow(mock_user, user_project):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_user

    with patch("app.api.routes.chat.orchestrator") as mock_graph:
        mock_graph.astream = _mock_orchestrator_stream

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/stream",
                json={
                    "project_id": user_project.id,
                    "message": "Should we expand to enterprise?",
                    "mode": "advisor",
                },
            )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        event_types = [e["type"] for e in events]
        assert "session_created" in event_types
        assert "agent_draft" in event_types
        assert "consensus" in event_types
        assert "done" in event_types
        assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_boardroom_persists_messages(mock_user, user_project):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_user

    with patch("app.api.routes.chat.orchestrator") as mock_graph:
        mock_graph.astream = _mock_orchestrator_stream

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            stream_response = await ac.post(
                "/api/v1/chat/stream",
                json={
                    "project_id": user_project.id,
                    "message": "What is our next move?",
                    "mode": "advisor",
                },
            )

        app.dependency_overrides.clear()
        assert stream_response.status_code == 200

        session_id = None
        for payload in _parse_sse_events(stream_response.text):
            if payload.get("type") == "session_created":
                session_id = payload["session_id"]
                break
        assert session_id

        app.dependency_overrides[get_current_user] = override_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            messages_response = await ac.get(f"/api/v1/sessions/{session_id}/messages")
        app.dependency_overrides.clear()

        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert "niche strategy" in messages[1]["content"].lower()
