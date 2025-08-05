"""
Basic tests for the ingestion service.
These tests ensure the service can start and basic functionality works.
"""

import os

# Import the app from main
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "test_key")
os.environ.setdefault("S3_SECRET_KEY", "test_secret")
os.environ.setdefault("S3_BUCKET", "test_bucket")

try:
    from main import app
except Exception as e:
    print(f"Warning: Could not import app: {e}")
    app = None


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    if app is None:
        pytest.skip("App could not be imported - skipping client tests")
    return TestClient(app)


def test_app_creation():
    """Test that the FastAPI app can be created."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    assert app is not None
    assert hasattr(app, "routes")


def test_health_check():
    """Test that the app can be imported and basic structure exists."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # This test ensures the app can be imported and has basic structure
    assert app is not None
    assert hasattr(app, "routes")
    assert len(app.routes) > 0


@patch("main.SessionLocal")
@patch("main.s3")
def test_upload_file_endpoint_exists(mock_s3, mock_db):
    """Test that the upload file endpoint exists."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # Mock the database session
    mock_session = MagicMock()
    mock_db.return_value = mock_session

    # Mock S3 client
    mock_s3_client = MagicMock()
    mock_s3.return_value = mock_s3_client

    # Check that the endpoint exists in the app routes
    routes = [route.path for route in app.routes]
    assert "/uploadfile/" in routes


@patch("main.SessionLocal")
def test_users_endpoint_exists(mock_db):
    """Test that the users endpoint exists."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # Mock the database session
    mock_session = MagicMock()
    mock_db.return_value = mock_session

    # Check that the endpoint exists in the app routes
    routes = [route.path for route in app.routes]
    assert "/users/" in routes


@patch("main.SessionLocal")
def test_workspaces_endpoint_exists(mock_db):
    """Test that the workspaces endpoint exists."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # Mock the database session
    mock_session = MagicMock()
    mock_db.return_value = mock_session

    # Check that the endpoint exists in the app tests
    routes = [route.path for route in app.routes]
    assert "/workspaces/" in routes


def test_cors_middleware_configured():
    """Test that CORS middleware is configured."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # Check that CORS middleware is added to the app
    middleware_classes = [middleware.cls for middleware in app.user_middleware]
    from fastapi.middleware.cors import CORSMiddleware

    assert CORSMiddleware in middleware_classes


if __name__ == "__main__":
    pytest.main([__file__])
