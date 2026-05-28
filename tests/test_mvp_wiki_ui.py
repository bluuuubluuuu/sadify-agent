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


def test_api_ts_exports_new_list_shaped_wiki_types():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type WikiFilePreview" in api
    assert "export type WikiFileResult" in api
    assert "export type WikiBackupInfo" in api
    assert "files: WikiFilePreview[]" in api
    assert "changed_files: string[]" in api
    assert "first_time_write: boolean" in api
    assert "expected_remote_hashes: expectedRemoteHashes" in api
    assert "files: WikiFileResult[]" in api
    assert "backup: WikiBackupInfo" in api


def test_sad_preview_panel_builds_expected_hash_map_for_bulk_update():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "function expectedRemoteHashes" in panel
    assert "response.files" in panel
    assert "expected_remote_hashes" not in panel
    assert "commitWikiUpdate(idToken, expectedRemoteHashes(response), false)" in panel
    assert "commitWikiUpdate(" in panel
    assert "expectedRemoteHashes(wikiPreviewResponse)" in panel


def test_sad_preview_panel_renders_multi_file_wiki_update_result():
    panel = (WEB_SRC / "components" / "SadPreviewPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "wikiRecord.files.map" in panel
    assert "file.relative_path" in panel
    assert "file.web_view_link" in panel
    assert "wikiRecord.backup.created" in panel
    assert "wikiRecord.backup.path" in panel


def test_wiki_update_dialog_lists_changed_files_and_uses_bulk_overwrite_copy():
    dialog = (WEB_SRC / "components" / "WikiUpdateDialog.tsx").read_text(
        encoding="utf-8"
    )

    assert "preview.changed_files" in dialog
    assert "preview.files.filter" in dialog
    assert "file.remote_markdown" in dialog
    assert "file.proposed_markdown" in dialog
    assert "Overwrite all" in dialog
    assert "onConfirm(true)" in dialog
    assert "Cancel" in dialog


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
