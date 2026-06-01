from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_sad_save_ui_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useSadSave.ts",
        WEB_SRC / "components" / "preview" / "PreviewPane.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_sad_save_api_contract_is_wired():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type SadSaveApiResponse" in api
    assert "export async function saveSadPreview" in api
    assert "/sad/save" in api
    assert "Authorization: `Bearer ${idToken}`" in api
    assert "preview_id: previewId" in api


def test_sad_save_engine_and_pane_render_save_states():
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")
    pane = (WEB_SRC / "components" / "preview" / "PreviewPane.tsx").read_text(encoding="utf-8")

    assert "saveSadPreview" in save
    assert "getFirebaseAuth" in save
    assert "Saved to project repo." in save
    assert "Save to Drive" in pane
    assert "Saved to project repo" in pane
    assert "record.sad_doc.url" in pane
    assert "record.sad_doc.path" in pane


def test_sad_save_history_refresh_callback_is_wired():
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")

    assert "onHistoryRefresh" in save
    assert "setHistoryRefreshKey" in workspace
