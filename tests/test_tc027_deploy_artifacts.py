"""Static checks for the TC-027 two-service Cloud Run deploy artifacts.

These lock the deploy contract WITHOUT building or deploying anything:
- backend Dockerfile at the worktree ROOT (so the image can include both
  services/api/src and the root src/ sadify package the API imports);
- backend starts the uvicorn factory app;
- frontend Dockerfile uses the Next.js standalone output;
- dockerignore/gcloudignore exclude secrets, venv, node_modules, .next, caches;
- no secret/credential files are pulled into either build context.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_backend_dockerfile_at_root_includes_both_source_trees():
    # Root location is intentional: --source . gives Cloud Build a single
    # context that contains BOTH services/api/src and src/. A services/api
    # context could not reach ../../src.
    assert (ROOT / "Dockerfile").exists()
    dockerfile = _read("Dockerfile")
    assert "COPY services/api/src/" in dockerfile
    assert "COPY src/" in dockerfile
    assert "/app/services/api/src" in dockerfile
    assert "/app/src" in dockerfile


def test_backend_dockerfile_starts_uvicorn_factory():
    dockerfile = _read("Dockerfile")
    assert "sadify_api.main:create_app" in dockerfile
    assert "--factory" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert "${PORT:-8080}" in dockerfile


def test_backend_dockerfile_installs_api_runtime_libs_not_streamlit():
    # The API needs the lazy-imported extractor libs plus google-adk for the
    # TC-034 agent path. Streamlit / pandas are not on the API path and must
    # not bloat the image.
    dockerfile = _read("Dockerfile")
    for dep in ('"uvicorn', '"fastapi', '"pypdf', '"python-docx', '"openpyxl',
                '"google-cloud-firestore', '"google-cloud-secret-manager',
                '"google-adk', '"google-genai', '"firebase-admin',
                '"python-multipart',
                # MCP server (TC-034 GitHub path) needs mcp + httpx in the image.
                '"mcp', '"httpx'):
        assert dep in dockerfile
    assert '"streamlit' not in dockerfile
    assert '"pandas' not in dockerfile


def test_backend_dockerfile_bundles_mcp_server_for_subprocess():
    # The agent spawns `python -m services.mcp.github_server` as a stdio
    # subprocess; the image must contain that package and put /app on the path.
    dockerfile = _read("Dockerfile")
    assert "COPY services/mcp/" in dockerfile
    assert "services.mcp.github_server" in dockerfile or "/app/src:/app" in dockerfile
    assert (ROOT / "services" / "mcp" / "github_server.py").exists()


def test_backend_dockerfile_uses_explicit_copy_not_whole_context():
    # Explicit COPY of only the two source trees keeps .env / any stray files
    # out of the image even if they reach the build context.
    dockerfile = _read("Dockerfile")
    assert "COPY . ." not in dockerfile


def test_frontend_dockerfile_uses_next_standalone():
    assert (ROOT / "apps" / "web" / "Dockerfile").exists()
    dockerfile = _read("apps/web/Dockerfile")
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "/app/.next/standalone" in dockerfile
    assert "node server.js" in dockerfile


def test_frontend_dockerfile_passes_public_build_args():
    dockerfile = _read("apps/web/Dockerfile")
    for arg in (
        "NEXT_PUBLIC_SADIFY_API_BASE_URL",
        "NEXT_PUBLIC_FIREBASE_API_KEY",
        "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN",
        "NEXT_PUBLIC_FIREBASE_PROJECT_ID",
        "NEXT_PUBLIC_FIREBASE_APP_ID",
        "NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID",
    ):
        assert f"ARG {arg}" in dockerfile


def test_frontend_cloudbuild_bakes_public_args_and_pushes_image():
    # NEXT_PUBLIC_* are build-time, so the frontend image is built via Cloud
    # Build with --build-arg (gcloud run deploy --source cannot pass them).
    assert (ROOT / "apps" / "web" / "cloudbuild.yaml").exists()
    cloudbuild = _read("apps/web/cloudbuild.yaml")
    for arg in (
        "NEXT_PUBLIC_SADIFY_API_BASE_URL=",
        "NEXT_PUBLIC_FIREBASE_API_KEY=",
        "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=",
        "NEXT_PUBLIC_FIREBASE_PROJECT_ID=",
        "NEXT_PUBLIC_FIREBASE_APP_ID=",
        "NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=",
    ):
        assert f"--build-arg" in cloudbuild
        assert arg in cloudbuild
    # builds + pushes only; the actual run deploy stays a separate gated step,
    # so there is no gcloud deploy step (no `entrypoint: gcloud`). "gcloud run
    # deploy" appears only in the documented separate command in the comments.
    assert "images:" in cloudbuild
    assert "entrypoint: gcloud" not in cloudbuild


def test_frontend_dockerignore_excludes_build_junk_and_env():
    ignore = _read("apps/web/.dockerignore")
    for pattern in ("node_modules", ".next", ".env"):
        assert pattern in ignore


def test_frontend_gcloudignore_excludes_node_modules_and_next():
    ignore = _read("apps/web/.gcloudignore")
    assert "node_modules/" in ignore
    assert ".next/" in ignore


def test_root_gcloudignore_excludes_secrets_caches_and_non_api_trees():
    ignore = _read(".gcloudignore")
    for pattern in (
        ".env",
        ".venv/",
        "node_modules/",
        "__pycache__/",
        ".pytest_cache/",
        "docs/",
        # backend context only needs services/api/src + src
        "apps/",
        "tests/",
        "sadify_agent/",
    ):
        assert pattern in ignore


def test_no_secret_or_credential_files_in_build_contexts():
    # Worktree root (backend context) and apps/web (frontend context) must not
    # contain service-account keys or .secrets. Real secrets live in the main
    # repo, outside both contexts.
    assert not (ROOT / ".secrets").exists()
    stray = [
        path
        for path in ROOT.glob("*.json")
        if "adminsdk" in path.name.lower() or "credential" in path.name.lower()
    ]
    assert stray == []
    web = ROOT / "apps" / "web"
    web_creds = [
        path
        for path in web.rglob("*.json")
        if "node_modules" not in path.parts
        and ("adminsdk" in path.name.lower() or "credential" in path.name.lower())
    ]
    assert web_creds == []
