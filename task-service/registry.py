import os

PARSING_SERVICE_URL = os.getenv(
    "PARSING_SERVICE_URL", "http://document-parsing-service:8005"
)
CHUNKING_SERVICE_URL = os.getenv(
    "CHUNKING_SERVICE_URL", "http://chunking-service:8006"
)
REDACTION_SERVICE_URL = os.getenv(
    "REDACTION_SERVICE_URL", "http://redaction-service:8007"
)
EMBEDDING_SERVICE_URL = os.getenv(
    "EMBEDDING_SERVICE_URL", "http://embedding-service:8001"
)
INDEX_DOCUMENT_SERVICE_URL = os.getenv(
    "INDEX_DOCUMENT_SERVICE_URL", "http://index-document-service:8011"
)
INDEXING_SERVICE_URL = os.getenv(
    "INDEXING_SERVICE_URL", "http://indexing-service:8012"
)

# Keys are lowercase task names
REGISTRY: dict[str, dict] = {
    # Internal example handled by this service
    "hello-world": {
        "type": "internal",
        "handler": "hello_world",
    },
    # Pipeline orchestrator
    "index-document": {
        "type": "http",
        "method": "POST",
        "url": f"{INDEX_DOCUMENT_SERVICE_URL}/",
    },
    # Worker tasks
    "parse-document": {
        "type": "http",
        "method": "POST",
        "url": f"{PARSING_SERVICE_URL}/parse",
    },
    "redact": {
        "type": "http",
        "method": "POST",
        "url": f"{REDACTION_SERVICE_URL}/redact",
    },
    "chunk": {
        "type": "http",
        "method": "POST",
        "url": f"{CHUNKING_SERVICE_URL}/chunk",
    },
    "embed": {
        "type": "http",
        "method": "POST",
        "url": f"{EMBEDDING_SERVICE_URL}/embed-chunk",
    },
    "index": {
        "type": "http",
        "method": "POST",
        "url": f"{INDEXING_SERVICE_URL}/index-chunk",
    },
}
