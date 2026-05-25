from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_sad_save_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "SadPreviewPanel.tsx",
        WEB_SRC / "components" / "WorkspaceShell.tsx",
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


def test_sad_save_button_renders_after_preview():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "saveSadPreview" in panel
    assert "Save to project repo" in panel
    assert "previewResponse ?" in panel
    assert "getFirebaseAuth" in panel


def test_sad_save_renders_saved_and_error_states():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "Saved to project repo" in panel
    assert "record.sad_doc.url" in panel
    assert "record.sad_doc.path" in panel
    assert "saveMessage" in panel


def test_sad_save_state_resets_when_preview_is_regenerated():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    create_preview_body = panel.split("async function createPreview()", 1)[1].split(
        "async function savePreviewToProjectRepo", 1
    )[0]
    set_preview_index = create_preview_body.index("setPreviewResponse(response);")
    success_tail = create_preview_body[set_preview_index:].split("    } catch", 1)[0]

    assert "setSaveResponse(null);" in success_tail
    assert "setSaveMessage(" in success_tail


def test_workspace_tracking_updates_after_sad_save():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )

    assert "SadSaveApiResponse" in shell
    assert "applySadSaved" in shell
    assert "onSadSaved={applySadSaved}" in shell
    assert "Google Doc placeholder" in shell
