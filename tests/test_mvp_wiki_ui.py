from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_wiki_ui_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useSadSave.ts",
        WEB_SRC / "components" / "preview" / "WikiDialog.tsx",
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


def test_use_sad_save_builds_expected_hash_map_for_bulk_update():
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")

    assert "function expectedRemoteHashes" in save
    assert "previewWikiUpdate" in save
    assert "commitWikiUpdate(idToken, expectedRemoteHashes(response), false)" in save
    assert "expectedRemoteHashes(wikiPreviewResponse)" in save
    assert "requires_confirmation" in save


def test_wiki_dialog_lists_changed_files_and_uses_bulk_overwrite_copy():
    dialog = (WEB_SRC / "components" / "preview" / "WikiDialog.tsx").read_text(encoding="utf-8")

    assert "preview.changed_files" in dialog
    assert "preview.files.map" in dialog
    assert "proposed_markdown" in dialog
    assert "requires_confirmation" in dialog
    assert "onConfirm(true)" in dialog
    assert "Cancel" in dialog


def test_wiki_state_resets_when_preview_is_regenerated():
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")

    assert "setWikiPreviewResponse(null)" in save
    assert "setWikiUpdateResponse(null)" in save
    assert "setWikiDialogOpen(false)" in save
