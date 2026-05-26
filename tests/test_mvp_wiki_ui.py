from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_wiki_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "SadPreviewPanel.tsx",
        WEB_SRC / "components" / "WikiUpdateDialog.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_api_ts_exports_wiki_preview_and_commit_functions():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type WikiPreviewResponse" in api
    assert "export type WikiUpdateResponse" in api
    assert "export async function previewWikiUpdate" in api
    assert "export async function commitWikiUpdate" in api
    assert "/sad/wiki/preview" in api
    assert "/sad/wiki/update" in api


def test_sad_preview_panel_renders_update_wiki_button_after_save():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "previewWikiUpdate" in panel
    assert "commitWikiUpdate" in panel
    assert "isGoogleOAuthConfigured" in panel
    assert "Update wiki" in panel
    assert "saveResponse && isGoogleOAuthConfigured()" in panel


def test_wiki_update_dialog_renders_diff_when_conflict_present():
    dialog = (WEB_SRC / "components" / "WikiUpdateDialog.tsx").read_text(
        encoding="utf-8"
    )

    assert "remote_markdown" in dialog
    assert "proposed_markdown" in dialog
    assert "Overwrite wiki" in dialog
    assert "Cancel" in dialog
    assert "remoteLines" in dialog
    assert "proposedLines" in dialog


def test_wiki_state_resets_when_preview_is_regenerated():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    create_preview_body = panel.split("async function createPreview()", 1)[1].split(
        "async function savePreviewToProjectRepo", 1
    )[0]
    set_preview_index = create_preview_body.index("setPreviewResponse(response);")
    success_tail = create_preview_body[set_preview_index:].split("    } catch", 1)[0]

    assert "setWikiPreviewResponse(null);" in success_tail
    assert "setWikiUpdateResponse(null);" in success_tail
    assert "setWikiDialogOpen(false);" in success_tail
