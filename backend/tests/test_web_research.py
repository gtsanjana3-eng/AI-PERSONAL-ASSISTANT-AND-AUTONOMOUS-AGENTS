import pytest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.tools.web_research import web_search
from backend.agents.orchestrator import AgentState, TaskStatus

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_search():
    old_provider = settings.SEARCH_PROVIDER
    settings.SEARCH_PROVIDER = "wikipedia"
    yield
    settings.SEARCH_PROVIDER = old_provider

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        
    def json(self):
        return self.json_data
        
    def raise_for_status(self):
        if self.status_code != 200:
            raise httpx.HTTPStatusError("HTTP Error", request=None, response=self)

def test_web_search_unavailable():
    settings.SEARCH_PROVIDER = ""
    res = web_search("test")
    assert "unavailable" in res.lower()

def test_web_search_empty():
    res = web_search("   ")
    assert "Empty" in res

def test_web_search_timeout():
    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Timeout")):
        res = web_search("test")
        assert "timed out" in res.lower()

def test_web_search_success():
    mock_resp = MockResponse({
        "query": {
            "search": [
                {"title": "Mock Title", "snippet": "Mock snippet"}
            ]
        }
    })
    
    with patch("httpx.Client.get", return_value=mock_resp):
        res = web_search("test query")
        assert "Title: Mock Title" in res
        assert "Snippet: Mock snippet" in res

def test_web_search_no_results():
    mock_resp = MockResponse({"query": {"search": []}})
    with patch("httpx.Client.get", return_value=mock_resp):
        res = web_search("test query")
        assert "No results found" in res

def test_orchestrator_research_fallback():
    # Test that the fallback planner maps "research" queries to web_search tool correctly
    mock_resp = MockResponse({
        "query": {
            "search": [
                {"title": "Orchestrator", "snippet": "Fallback"}
            ]
        }
    })
    
    with patch("httpx.Client.get", return_value=mock_resp):
        response = client.post("/api/chat", json={"message": "research something"})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "research"
        assert data["planner_source"] == "fallback"
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["tool_name"] == "web_search"
        assert data["tasks"][0]["status"] == TaskStatus.COMPLETED
        assert "Title: Orchestrator" in data["tasks"][0]["result"]
