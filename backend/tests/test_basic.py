from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200


def test_chat_endpoint():
    response = client.post(
        "/api/chat",
        json={"message": "hello"}
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert "state" in data
    assert "tasks" in data


def test_chat_endpoint_invalid_input():
    response = client.post(
        "/api/chat",
        json={"message": "   "}
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == "Message cannot be empty."


def test_chat_endpoint_missing_message():
    response = client.post(
        "/api/chat",
        json={}
    )

    assert response.status_code == 422


def test_chat_endpoint_message_too_long():
    long_message = "a" * 2001

    response = client.post(
        "/api/chat",
        json={"message": long_message}
    )

    assert response.status_code == 422


def test_chat_endpoint_valid_message():
    response = client.post(
        "/api/chat",
        json={"message": "add 2 and 3"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["state"] == "COMPLETED"


def test_history_endpoint():
    response = client.get("/api/history")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


def test_history_limit():
    response = client.get("/api/history?limit=5")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 5


def test_history_limit_is_capped():
    response = client.get("/api/history?limit=1000")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


def test_history_detail_not_found():
    response = client.get(
        "/api/history/non-existent-plan-id"
    )

    assert response.status_code == 404
def test_unknown_tool_is_rejected():
    from backend.tools.registry import registry

    assert registry.get_tool("delete_system_files") is None
    assert registry.validate_tool_call(
        "delete_system_files",
        {}
    ) is False
def test_orchestrator_rejects_unregistered_tool():
    from backend.agents.orchestrator import AgentOrchestrator, _plans_db

    orchestrator = AgentOrchestrator()

    plan = orchestrator._mock_planner("fail")

    _plans_db[plan.id] = plan

    result = orchestrator._resume_plan(plan.id)

    assert result["state"] == "FAILED"
    assert "not registered" in result["error"]
def test_tools_endpoint():
    response = client.get("/api/tools")

    assert response.status_code == 200

    data = response.json()

    assert "tools" in data
    assert isinstance(data["tools"], list)

    tool_names = {
        tool["name"]
        for tool in data["tools"]
    }

    assert "add" in tool_names
    assert "subtract" in tool_names
    assert "create_note" in tool_names
    assert "delete_all_notes" in tool_names
    assert "web_search" in tool_names
def test_approve_nonexistent_plan():
    response = client.post(
        "/api/approve",
        json={
            "plan_id": "non-existent-plan",
            "task_id": 1
        }
    )

    assert response.status_code == 404


def test_reject_nonexistent_plan():
    response = client.post(
        "/api/reject",
        json={
            "plan_id": "non-existent-plan",
            "task_id": 1
        }
    )

    assert response.status_code == 404


def test_approve_invalid_task_id():
    response = client.post(
        "/api/approve",
        json={
            "plan_id": "test-plan",
            "task_id": 0
        }
    )

    assert response.status_code == 422

def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "AI Personal Assistant"