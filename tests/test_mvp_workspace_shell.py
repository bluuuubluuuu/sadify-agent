from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_workspace_shell_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "WorkspaceV2.tsx",
        WEB_SRC / "components" / "shell" / "AppShell.tsx",
        WEB_SRC / "components" / "shell" / "Sidebar.tsx",
        WEB_SRC / "components" / "chat" / "ChatPanel.tsx",
        WEB_SRC / "components" / "chat" / "ReadinessPane.tsx",
        WEB_SRC / "components" / "preview" / "PreviewPane.tsx",
        WEB_SRC / "lib" / "stage.ts",
    ]
    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]
    assert missing == []


def test_workspace_v2_composes_shell_chat_preview():
    page = (WEB_SRC / "app" / "page.tsx").read_text(encoding="utf-8")
    shell = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")
    app_shell = (WEB_SRC / "components" / "shell" / "AppShell.tsx").read_text(encoding="utf-8")

    assert "WorkspaceV2" in page
    assert "AppShell" in shell
    assert "Sidebar" in shell
    assert "ChatPanel" in shell
    assert "PreviewPane" in shell
    assert "deriveStage" in shell
    assert "data-stage" in app_shell


def test_scrollbars_use_light_workspace_tone():
    globals_css = (WEB_SRC / "app" / "globals.css").read_text(encoding="utf-8")

    assert "scrollbar-color" in globals_css
    assert "#cbd5e1" in globals_css
    assert "::-webkit-scrollbar-thumb" in globals_css
