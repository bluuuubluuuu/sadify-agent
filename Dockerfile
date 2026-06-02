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
# openpyxl). streamlit / google-adk / pandas are NOT needed on the API path.
RUN pip install --no-cache-dir \
    "fastapi>=0.124.0" \
    "google-api-python-client>=2.130,<3" \
    "google-auth>=2.30,<3" \
    "google-auth-oauthlib>=1.2,<2" \
    "google-cloud-firestore>=2.20,<3" \
    "google-cloud-secret-manager>=2.20,<3" \
    "google-genai>=1.40,<2" \
    "firebase-admin>=7.0,<8" \
    "uvicorn[standard]>=0.38.0" \
    "python-multipart>=0.0.20,<1" \
    "pydantic>=2.13.0" \
    "pypdf>=6.10.0" \
    "python-docx>=1.2.0" \
    "openpyxl>=3.1.0"

# Source trees (run via PYTHONPATH, same as the local dev/test setup).
COPY services/api/src/ ./services/api/src/
COPY src/ ./src/

ENV PYTHONPATH="/app/services/api/src:/app/src" \
    PYTHONUNBUFFERED=1

# Cloud Run injects PORT (default 8080). Factory app, ADC credentials.
CMD ["sh", "-c", "exec uvicorn sadify_api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
