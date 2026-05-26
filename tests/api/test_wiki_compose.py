from datetime import UTC, datetime

from sadify_api.schemas import DriveRepoRecord, SadSaveRecord, SourceRecord
from sadify_api.services.drive_repo import DEFAULT_PROJECT_REPO_STRUCTURE
from sadify_api.services.wiki_compose import compose_wiki_markdown


def test_compose_includes_project_name_and_requirement_text():
    markdown = _compose()

    assert "# SADify Project Wiki" in markdown
    assert "**Project repo:** SADify Projects" in markdown
    assert "A workshop tracks repairs from drop-off to collection." in markdown


def test_compose_links_to_latest_sad_doc_url():
    markdown = _compose()

    assert "[SP-000002](https://docs.google.com/document/d/doc-002/edit)" in markdown


def test_compose_lists_saved_sad_ids_in_order():
    first = _save("SV-000001", "SP-000001", "doc-001", 1)
    second = _save("SV-000002", "SP-000002", "doc-002", 2)

    markdown = compose_wiki_markdown(
        repo=_repo(),
        latest_save=second,
        all_saves_for_repo=[first, second],
        sources=[],
        requirement_text="Track repairs.",
    )

    first_index = markdown.index("- SV-000001")
    second_index = markdown.index("- SV-000002")
    assert first_index < second_index


def test_compose_includes_one_line_section_summaries():
    markdown = _compose()

    assert "### Section summaries" in markdown
    assert "- **Phone Repair SAD:** 3 sections saved for this SAD preview." in markdown


def test_compose_lists_source_file_names_when_present():
    markdown = _compose(sources=[_source("SRC-000001", "repair workflow.pdf")])

    assert "## Sources" in markdown
    assert "- repair workflow.pdf" in markdown


def test_compose_handles_no_sources():
    markdown = _compose(sources=[])

    assert "## Sources" in markdown
    assert "- No uploaded sources linked to the latest saved SAD." in markdown


def test_compose_handles_missing_assumptions():
    markdown = _compose(latest_save=_save("SV-000002", "SP-000002", "doc-002", 2))

    assert "## Latest SAD" in markdown
    assert "## Save history" in markdown


def test_compose_returns_pure_markdown_with_no_html_tags():
    markdown = _compose(
        requirement_text="Track <b>repair</b> jobs.",
        sources=[_source("SRC-000001", "<script>bad</script>.pdf")],
    )

    assert "<b>" not in markdown
    assert "</b>" not in markdown
    assert "<script>" not in markdown


def _compose(
    *,
    latest_save: SadSaveRecord | None = None,
    sources: list[SourceRecord] | None = None,
    requirement_text: str = "A workshop tracks repairs from drop-off to collection.",
) -> str:
    latest = latest_save or _save("SV-000002", "SP-000002", "doc-002", 2)
    return compose_wiki_markdown(
        repo=_repo(),
        latest_save=latest,
        all_saves_for_repo=[
            _save("SV-000001", "SP-000001", "doc-001", 1),
            latest,
        ],
        sources=sources or [],
        requirement_text=requirement_text,
    )


def _repo() -> DriveRepoRecord:
    now = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)
    return DriveRepoRecord(
        grant_id="DG-000001",
        project_id="PROJ-000001",
        owner_uid="firebase-uid-001",
        owner_email="owner@example.com",
        status="connected",
        repo_folder_id="drive-folder-001",
        repo_folder_name="SADify Projects",
        repo_url="https://drive.google.com/drive/folders/drive-folder-001",
        requested_scopes=["https://www.googleapis.com/auth/drive.file"],
        folder_structure=list(DEFAULT_PROJECT_REPO_STRUCTURE),
        token_store="secret_manager",
        saves_blocked=False,
        created_at=now,
        updated_at=now,
    )


def _save(
    save_id: str,
    preview_id: str,
    doc_id: str,
    day: int,
    *,
    section_count: int = 3,
) -> SadSaveRecord:
    now = datetime(2026, 5, day, 10, 0, tzinfo=UTC)
    artifact = {
        "artifact_id": f"SA-{save_id[-6:]}",
        "artifact_type": "google_doc",
        "title": "Phone Repair SAD",
        "path": f"SAD/{preview_id}-{save_id}.google_doc",
        "file_id": doc_id,
        "url": f"https://docs.google.com/document/d/{doc_id}/edit",
        "mime_type": "application/vnd.google-apps.document",
        "source_ids": [],
        "created_at": now,
    }
    manifest = {
        "manifest_id": f"SM-{save_id[-6:]}",
        "repo_grant_id": "DG-000001",
        "repo_folder_id": "drive-folder-001",
        "repo_folder_name": "SADify Projects",
        "preview_id": preview_id,
        "preview_revision": now.isoformat(),
        "analysis_id": "AN-000001",
        "requirement_text": "A workshop tracks repairs.",
        "sad_title": "Phone Repair SAD",
        "preview_section_count": section_count,
        "preview_assumption_count": 0,
        "preview_open_question_count": 0,
        "preview_source_references": [],
        "source_ids": [],
        "artifact_paths": [artifact["path"]],
        "saved_at": now,
    }
    return SadSaveRecord.model_validate(
        {
            "save_id": save_id,
            "idempotency_key": f"firebase-uid-001|DG-000001|{preview_id}|{now.isoformat()}",
            "owner_uid": "firebase-uid-001",
            "owner_email": "owner@example.com",
            "project_id": "PROJ-000001",
            "repo_grant_id": "DG-000001",
            "repo_folder_id": "drive-folder-001",
            "repo_folder_name": "SADify Projects",
            "preview_id": preview_id,
            "preview_revision": now.isoformat(),
            "status": "saved",
            "sad_doc": artifact,
            "artifacts": [artifact],
            "manifest": manifest,
            "change_summary": "Saved.",
            "source_artifact_references": [],
            "created_at": now,
            "updated_at": now,
        }
    )


def _source(source_id: str, filename: str) -> SourceRecord:
    now = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)
    return SourceRecord(
        source_id=source_id,
        source_item_id=f"{source_id}-ITEM",
        source_type="pdf",
        original_file_name=filename,
        mime_type="application/pdf",
        file_size_bytes=128,
        drive_file_id=None,
        extraction_status="extracted",
        extracted_text_preview="workflow",
        extracted_text="workflow",
        extraction_summary="workflow extracted",
        traceability_units=[],
        created_at=now,
        updated_at=now,
    )
