import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
import json

client = TestClient(app)

@pytest.fixture(autouse=True)
def enable_llm():
    old_enabled = settings.LLM_ENABLED
    old_key = settings.LLM_API_KEY
    settings.LLM_ENABLED = True
    settings.LLM_API_KEY = "test_key"
    yield
    settings.LLM_ENABLED = old_enabled
    settings.LLM_API_KEY = old_key

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        
    def json(self):
        return self.json_data
        
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("HTTP Error")

def test_llm_valid_plan():
    llm_plan = {
        "intent": "llm_calculation",
        "tasks": [
            {
                "id": 1,
                "description": "Add via LLM",
                "tool_name": "add",
                "tool_args": {"a": 10, "b": 20}
            }
        ]
    }
    
    with patch("backend.agents.llm_service.call_llm_planner", return_value=llm_plan):
        response = client.post("/api/chat", json={"message": "add 10 and 20"})
        assert response.status_code == 200
        data = response.json()
        assert data.get("planner_source") == "ai"
        assert data.get("intent") == "llm_calculation"
        assert data["tasks"][0]["result"] == 30

def test_llm_malformed_plan():
    with patch("backend.agents.llm_service.call_llm_planner", return_value=None):
        response = client.post("/api/chat", json={"message": "add 2 and 3"})
        data = response.json()
        # Should fallback to mock planner
        assert data.get("planner_source") == "fallback"
        assert data.get("intent") == "calculation"

def test_llm_unknown_tool():
    from backend.agents.llm_service import call_llm_planner
    content = json.dumps({
        "intent": "do stuff",
        "tasks": [{"id": 1, "description": "stuff", "tool_name": "invented_tool", "tool_args": {}}]
    })
    mock_resp = MockResponse({"choices": [{"message": {"content": content}}]})
    
    # Test llm_service directly without TestClient to avoid httpx conflict
    with patch("httpx.Client.post", return_value=mock_resp):
        res = call_llm_planner("do stuff")
        assert res is None # validation failed
        
    # Test fallback works through orchestrator
    with patch("backend.agents.llm_service.call_llm_planner", return_value=None):
        response = client.post("/api/chat", json={"message": "add 2 and 3"})
        assert response.json().get("planner_source") == "fallback"

def test_llm_timeout_fallback():
    from backend.agents.llm_service import call_llm_planner
    with patch("httpx.Client.post", side_effect=Exception("Timeout")):
        res = call_llm_planner("add 2 and 3")
        assert res is None

def test_missing_api_key():
    settings.LLM_API_KEY = ""
    response = client.post("/api/chat", json={"message": "add 2 and 3"})
    data = response.json()
    assert data.get("planner_source") == "fallback"
def test_llm_rejects_unknown_tool():
    from backend.agents.llm_service import _validate_plan

    malicious_plan = {
        "intent": "dangerous action",
        "tasks": [
            {
                "id": 1,
                "description": "Run an unknown tool",
                "tool_name": "delete_system_files",
                "tool_args": {}
            }
        ]
    }

    assert _validate_plan(malicious_plan) is False


def test_llm_rejects_invalid_tool_arguments():
    from backend.agents.llm_service import _validate_plan

    invalid_plan = {
        "intent": "calculation",
        "tasks": [
            {
                "id": 1,
                "description": "Add numbers",
                "tool_name": "add",
                "tool_args": {
                    "wrong_argument": 100
                }
            }
        ]
    }

    assert _validate_plan(invalid_plan) is False


def test_llm_accepts_valid_tool_plan():
    from backend.agents.llm_service import _validate_plan

    valid_plan = {
        "intent": "calculation",
        "tasks": [
            {
                "id": 1,
                "description": "Add two numbers",
                "tool_name": "add",
                "tool_args": {
                    "a": 10,
                    "b": 20
                }
            }
        ]
    }

    assert _validate_plan(valid_plan) is True
def test_llm_rejects_wrong_argument_types():
    from backend.agents.llm_service import _validate_plan

    invalid_plan = {
        "intent": "calculation",
        "tasks": [{
            "id": 1,
            "description": "Add two numbers",
            "tool_name": "add",
            "tool_args": {
                "a": "hello",
                "b": "world"
            }
        }]
    }

    assert _validate_plan(invalid_plan) is False


def test_llm_accepts_numeric_argument_types():
    from backend.agents.llm_service import _validate_plan

    valid_plan = {
        "intent": "calculation",
        "tasks": [{
            "id": 1,
            "description": "Add two numbers",
            "tool_name": "add",
            "tool_args": {
                "a": 10,
                "b": 20
            }
        }]
    }

    assert _validate_plan(valid_plan) is True
