from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_workspace_shell_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "WorkspaceShell.tsx",
        WEB_SRC / "components" / "CurrentQuestion.tsx",
        WEB_SRC / "components" / "ReadinessPanel.tsx",
        WEB_SRC / "components" / "ChangeSummary.tsx",
        WEB_SRC / "lib" / "mockState.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_workspace_shell_renders_qna_readiness_and_tracking():
    page = (WEB_SRC / "app" / "page.tsx").read_text(encoding="utf-8")
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    mock_state = (WEB_SRC / "lib" / "mockState.ts").read_text(encoding="utf-8")
    change_summary = (WEB_SRC / "components" / "ChangeSummary.tsx").read_text(
        encoding="utf-8"
    )

    assert "WorkspaceShell" in page
    assert "CurrentQuestion" not in shell
    assert "No analysis yet" in shell
    assert "analysis-empty-state" in shell
    assert "ReadinessPanel" not in shell
    assert "ChangeSummary" in shell
    assert 'readinessLabel: "No analysis yet"' in mock_state
    assert 'text: ""' in mock_state
    assert "categories: []" in mock_state
    assert "Amend answer" in (WEB_SRC / "components" / "CurrentQuestion.tsx").read_text(
        encoding="utf-8"
    )
    assert "<details" in change_summary
