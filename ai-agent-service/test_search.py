#!/usr/bin/env python3
"""
Test script to debug search functionality in the AI agent service.
Run this from within the Docker container or with proper network access.
"""

import requests

# Service URLs (adjust if running from outside Docker)
AI_AGENT_URL = "http://localhost:8002"
EMBEDDING_SERVICE_URL = "http://localhost:8001"
INGESTION_SERVICE_URL = "http://localhost:8000"


def test_services():
    """Test basic service connectivity."""
    print("🔍 Testing service connectivity...")

    # Test AI Agent Service
    try:
        resp = requests.get(f"{AI_AGENT_URL}/health", timeout=5)
        print(f"✅ AI Agent Service: {resp.status_code}")
    except Exception as e:
        print(f"❌ AI Agent Service: {e}")
        return False

    # Test Embedding Service
    try:
        resp = requests.get(f"{EMBEDDING_SERVICE_URL}/health", timeout=5)
        print(f"✅ Embedding Service: {resp.status_code}")
    except Exception as e:
        print(f"❌ Embedding Service: {e}")
        return False

    # Test Ingestion Service
    try:
        resp = requests.get(f"{INGESTION_SERVICE_URL}/health", timeout=5)
        print(f"✅ Ingestion Service: {resp.status_code}")
    except Exception as e:
        print(f"❌ Ingestion Service: {e}")
        return False

    return True


def test_workspaces():
    """Test workspace retrieval."""
    print("\n🏢 Testing workspace retrieval...")

    try:
        resp = requests.get(f"{AI_AGENT_URL}/workspaces", timeout=10)
        if resp.status_code == 200:
            workspaces = resp.json()
            print(f"✅ Found {len(workspaces)} workspaces:")
            for ws in workspaces:
                print(f"   - ID: {ws['workspace_id']}, Name: {ws['name']}")
            return workspaces
        else:
            print(f"❌ Failed to get workspaces: {resp.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting workspaces: {e}")
        return []


def test_search(workspace_id, query="test"):
    """Test search functionality."""
    print(
        f"\n🔍 Testing search in workspace {workspace_id} with query: '{query}'"
    )

    try:
        # Test the test-search endpoint
        resp = requests.get(
            f"{AI_AGENT_URL}/test-search/{workspace_id}",
            params={"query": query, "top_k": 3},
            timeout=15,
        )

        if resp.status_code == 200:
            result = resp.json()
            print("✅ Search successful:")
            print(f"   Query: {result['query']}")
            print(f"   Workspace: {result['workspace_id']}")
            print(f"   Results: {result['total_results']}")

            if result['results']:
                print("   Documents found:")
                for doc in result['results']:
                    print(f"     - {doc['s3_key']} (Score: {doc['score']:.3f})")
                    print(f"       Content preview: {doc['content_preview'][:100]}...")
            else:
                print("   No documents found")

            return result
        else:
            print(f"❌ Search failed: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return None


def test_conversation(workspace_id, message="Hello, can you help me?"):
    """Test conversation endpoint."""
    print(f"\n💬 Testing conversation in workspace {workspace_id}")

    try:
        resp = requests.post(
            f"{AI_AGENT_URL}/conversation",
            json={
                "messages": [{"role": "user", "content": message}],
                "workspace_id": workspace_id,
            },
            timeout=30,
        )

        if resp.status_code == 200:
            result = resp.json()
            print("✅ Conversation successful:")
            print(f"   Response: {result['response'][:200]}...")
            print(f"   Documents retrieved: {len(result['relevant_docs'])}")

            if result['relevant_docs']:
                print("   Retrieved documents:")
                for doc in result['relevant_docs']:
                    print(f"     - {doc['s3_key']} (Score: {doc['score']:.3f})")
            else:
                print("   No documents were retrieved")

            return result
        else:
            print(f"❌ Conversation failed: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Error during conversation: {e}")
        return None


def main():
    """Main test function."""
    print("🚀 AI Agent Service Search Debug Tool")
    print("=" * 50)

    # Test basic connectivity
    if not test_services():
        print(
            "\n❌ Service connectivity test failed. Check your Docker setup."
        )
        return

    # Test workspace retrieval
    workspaces = test_workspaces()
    if not workspaces:
        print(
            "\n❌ No workspaces found. Make sure you have workspaces and documents uploaded."
        )
        return

    # Test search in first workspace
    workspace_id = workspaces[0]["workspace_id"]

    # Test with different queries
    test_queries = [
        "test",
        "help",
        "information",
        "document",
        "customer service",
    ]

    for query in test_queries:
        test_search(workspace_id, query)

    # Test conversation
    test_conversation(workspace_id, "Can you tell me about your services?")

    print("\n✅ Debug testing completed!")


if __name__ == "__main__":
    main()
