FROM python:3.11-slim

# Install minimal OS deps
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip setuptools wheel
RUN pip install fastapi uvicorn pydantic boto3 httpx

# --- Conditional installs based on parser versions (build-time) ---
# NOTE: To use these at build time, pass build args from compose, example:
#   services:
#     document-parsing-service:
#       build:
#         context: ./document-parsing-service
#         args:
#           PDF_PARSER_VERSION: ${PDF_PARSER_VERSION}
#           DOCX_PARSER_VERSION: ${DOCX_PARSER_VERSION}
#

ARG PDF_PARSER_VERSION
ARG DOCX_PARSER_VERSION
ENV PDF_PARSER_VERSION=${PDF_PARSER_VERSION}
ENV DOCX_PARSER_VERSION=${DOCX_PARSER_VERSION}

RUN set -eux; \
    if echo "$PDF_PARSER_VERSION" | grep -Eq '^complete-pdf-parser-' || echo "$DOCX_PARSER_VERSION" | grep -Eq '^complete-docx-parser-'; then \
        pip install filetype pandas lxml pypdfium2 python-docx python-pptx pillow openpyxl tqdm requests typer pydantic pydantic-settings marko beautifulsoup4 pylatexenc rtree certifi pluggy scipy && \
        pip install pyyaml tabulate jsonschema opencv-python-headless && \
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
        pip install accelerate transformers && \
        pip install --no-deps docling-core docling_ibm_models docling-parse docling; \
    fi

RUN set -eux; \
    if echo "$PDF_PARSER_VERSION" | grep -Eq '^fast-pdf-parser-'; then \
        pip install PyMuPDF; \
    fi

RUN set -eux; \
    if echo "$DOCX_PARSER_VERSION" | grep -Eq '^fast-docx-parser-'; then \
        pip install python-docx; \
    fi

COPY main.py .
COPY src ./src

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"] 