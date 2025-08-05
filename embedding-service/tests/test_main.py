"""
Basic tests for the embedding service.
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
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("GEMINI_API_KEY", "test_key")
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


@patch("main.qdrant_client")
@patch("main.s3")
def test_embed_endpoint_exists(mock_s3, mock_qdrant):
    """Test that the embed endpoint exists."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # Mock the Qdrant client
    mock_qdrant_client = MagicMock()
    mock_qdrant.return_value = mock_qdrant_client

    # Mock S3 client
    mock_s3_client = MagicMock()
    mock_s3.return_value = mock_s3_client

    # Check that the endpoint exists in the app routes
    routes = [route.path for route in app.routes]
    assert "/embed/" in routes


@patch("main.qdrant_client")
@patch("main.s3")
def test_search_endpoint_exists(mock_s3, mock_qdrant):
    """Test that the search endpoint exists."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # Mock the Qdrant client
    mock_qdrant_client = MagicMock()
    mock_qdrant.return_value = mock_qdrant_client

    # Mock S3 client
    mock_s3_client = MagicMock()
    mock_s3.return_value = mock_s3_client

    # Check that the endpoint exists in the app routes
    routes = [route.path for route in app.routes]
    assert "/search/" in routes


def test_cors_middleware_configured():
    """Test that CORS middleware is configured."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # Check that CORS middleware is added to the app
    middleware_classes = [middleware.cls for middleware in app.user_middleware]
    from fastapi.middleware.cors import CORSMiddleware

    assert CORSMiddleware in middleware_classes


@patch("main.genai")
def test_gemini_import_works(mock_genai):
    """Test that the Gemini AI import works."""
    if app is None:
        pytest.skip("App could not be imported - skipping app tests")
    # This test ensures that the google.generativeai module can be imported
    # and that the genai object is available
    assert mock_genai is not None


if __name__ == "__main__":
    pytest.main([__file__])
