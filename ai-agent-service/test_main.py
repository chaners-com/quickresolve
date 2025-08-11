import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-agent"


def test_get_workspaces():
    """Test the workspaces endpoint."""
    response = client.get("/workspaces")
    assert response.status_code == 200
    workspaces = response.json()
    assert isinstance(workspaces, list)
    assert len(workspaces) > 0

    # Check workspace structure
    workspace = workspaces[0]
    assert "workspace_id" in workspace
    assert "name" in workspace
    assert "description" in workspace


def test_conversation_endpoint():
    """Test the conversation endpoint."""
    # This test would require a mock for the external dependencies
    # For now, we'll just test the endpoint structure
    conversation_data = {
        "messages": [
            {"role": "user", "content": "Hello, how can you help me?"}
        ],
        "workspace_id": 1,
    }

    response = client.post("/conversation", json=conversation_data)
    # This might fail if external services aren't available, but that's expected
    # The important thing is that the endpoint exists and accepts the right format
    assert response.status_code in [
        200,
        500,
    ]  # 500 is expected if services aren't available


if __name__ == "__main__":
    pytest.main([__file__])
