from pathlib import Path


def test_procfile_runs_streamlit_app_on_cloud_run_port():
    procfile = Path("Procfile").read_text(encoding="utf-8").strip()

    assert procfile.startswith("web: streamlit run src/sadify/app.py")
    assert "--server.address 0.0.0.0" in procfile
    assert "--server.port $PORT" in procfile
    assert "--browser.gatherUsageStats false" in procfile


def test_gcloudignore_excludes_local_secrets_docs_and_build_noise():
    patterns = set(Path(".gcloudignore").read_text(encoding="utf-8").splitlines())

    assert ".env" in patterns
    assert ".env.*" in patterns
    assert "!.env.example" in patterns
    assert ".venv/" in patterns
    assert "docs/" in patterns
    assert "tmp/" in patterns
    assert "__pycache__/" in patterns
    assert ".streamlit/secrets.toml" in patterns
