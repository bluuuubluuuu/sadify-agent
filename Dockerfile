# Backend (sadify-api) image for Cloud Run.
# Built from the worktree ROOT so it can include both source trees the API
# needs: services/api/src (sadify_api) and src (the sadify extractors package).
# Deploy: gcloud run deploy sadify-api --source . --region asia-southeast1
#
# Runs as the Cloud Run runtime service account (ADC) -- no key file.
FROM python:3.13-slim

WORKDIR /app

# Dependencies mirror services/api/pyproject.toml plus the three lazy-imported
# extractor libs used by sadify.extractors.business_files (pypdf / python-docx /
# openpyxl). google-adk is included for the TC-034 API-hosted agent path.
# streamlit / pandas are NOT needed on the API path.
RUN pip install --no-cache-dir \
    "fastapi>=0.124.0" \
    "google-api-python-client>=2.130,<3" \
    "google-auth>=2.30,<3" \
    "google-auth-oauthlib>=1.2,<2" \
    "google-cloud-firestore>=2.20,<3" \
    "google-cloud-secret-manager>=2.20,<3" \
    "google-adk>=1.32.0,<2" \
    "google-genai>=1.40,<2" \
    "firebase-admin>=7.0,<8" \
    "uvicorn[standard]>=0.38.0" \
    "python-multipart>=0.0.20,<1" \
    "pydantic>=2.13.0" \
    "pypdf>=6.10.0" \
    "python-docx>=1.2.0" \
    "openpyxl>=3.1.0" \
    "mcp>=1.20.0,<2" \
    "httpx>=0.27,<1"

# Source trees (run via PYTHONPATH, same as the local dev/test setup).
# services/mcp is the stdio MCP server the agent spawns as a subprocess
# (python -m services.mcp.github_server) for the TC-034 GitHub-issues path.
COPY services/api/src/ ./services/api/src/
COPY services/mcp/ ./services/mcp/
COPY src/ ./src/

# /app is on the path so `python -m services.mcp.github_server` resolves the
# MCP server package in the subprocess (it also runs with cwd=/app).
ENV PYTHONPATH="/app/services/api/src:/app/src:/app" \
    PYTHONUNBUFFERED=1

# Cloud Run injects PORT (default 8080). Factory app, ADC credentials.
CMD ["sh", "-c", "exec uvicorn sadify_api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
