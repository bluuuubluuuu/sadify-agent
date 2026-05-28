from datetime import UTC, datetime

from sadify_api.schemas import (
    DriveRepoRecord,
    SadPreviewResponse,
    SadSaveRecord,
    SourceRecord,
)
from sadify_api.services.drive_repo import DEFAULT_PROJECT_REPO_STRUCTURE
from sadify_api.services.wiki_compose import compose_wiki_files


EXPECTED_FILE_ORDER = [
    "Wiki.md",
    "requirements.md",
    "actors.md",
    "workflows.md",
    "entities.md",
    "decisions.md",
    "reports.md",
    "sources.md",
]


def test_compose_returns_exact_managed_file_order():
    files = _compose()

    assert [file.name for file in files] == EXPECTED_FILE_ORDER
    assert [file.category for file in files] == [
        "index",
        "requirements",
        "actors",
        "workflows",
        "entities",
        "decisions",
        "reports",
        "sources",
    ]


def test_index_has_frontmatter_project_metadata_and_note_links():
    files = _compose(composed_at=datetime(2026, 5, 27, 9, 15, tzinfo=UTC))
    index = _by_name(files)["Wiki.md"]

    assert index.startswith("---\n")
    assert "title: SADify Project Wiki" in index
    assert "updated_at: '2026-05-27T09:15:00+00:00'" in index
    assert "project_repo: SADify Projects" in index
    assert "repo_grant_id: DG-000001" in index
    assert "latest_save_id: SV-000002" in index
    assert "[[requirements]]" in index
    assert "[[actors]]" in index
    assert "[[workflows]]" in index
    assert "[[entities]]" in index
    assert "[[decisions]]" in index
    assert "[[reports]]" in index
    assert "[[sources]]" in index
    assert "[SP-000002](https://docs.google.com/document/d/doc-002/edit)" in index


def test_notes_have_frontmatter_title_tags_and_updated_at():
    files = _compose(composed_at=datetime(2026, 5, 27, 9, 15, tzinfo=UTC))

    for file in files:
        assert file.markdown.startswith("---\n"), file.name
        assert "title: " in file.markdown, file.name
        assert "tags: [" in file.markdown, file.name
        assert "updated_at: '2026-05-27T09:15:00+00:00'" in file.markdown, file.name


def test_sections_route_to_domain_notes_by_normalized_title():
    files = _compose()
    by_name = _by_name(files)

    assert "## Goal and Scope" in by_name["requirements.md"]
    assert "Track repair jobs from drop-off through collection." in by_name["requirements.md"]
    assert "## Users and Roles" in by_name["actors.md"]
    assert "Counter staff create orders and technicians update repairs." in by_name["actors.md"]
    assert "## Access and Permissions" in by_name["actors.md"]
    assert "Owners can override payment corrections." in by_name["actors.md"]
    assert "## Workflow Steps: Repair Handoffs" in by_name["workflows.md"]
    assert "Handoff from counter to technician to pickup desk." in by_name["workflows.md"]
    assert "## Exceptions and Edge Cases" in by_name["workflows.md"]
    assert "Damaged parts and late pickups are flagged." in by_name["workflows.md"]
    assert "## Data and Records" in by_name["entities.md"]
    assert "Device, customer, parts, status, and payment records are stored." in by_name["entities.md"]
    assert "## Business Rules and Approvals" in by_name["decisions.md"]
    assert "Owner approval is required for refunds." in by_name["decisions.md"]
    assert "## Non-functional Needs" in by_name["decisions.md"]
    assert "Staff login and audit history are required." in by_name["decisions.md"]
    assert "## Reports and Summaries" in by_name["reports.md"]
    assert "Daily owner summary shows open jobs." in by_name["reports.md"]
    assert "## Integrations" in by_name["reports.md"]
    assert "No external integrations are needed in version one." in by_name["reports.md"]


def test_requirements_always_include_requirement_assumptions_and_open_questions():
    files = _compose()
    requirements = _by_name(files)["requirements.md"]

    assert "## Original Requirement" in requirements
    assert "Repair shop wants to track jobs, parts, statuses, and payments." in requirements
    assert "## Assumptions" in requirements
    assert "- SMS notification wording can be finalized later." in requirements
    assert "## Open Questions" in requirements
    assert "- Confirm who can waive diagnostic fees." in requirements


def test_unmatched_sections_go_to_requirements_other_without_loss():
    preview = _preview(
        [
            ("Deployment Notes", "Technicians prefer tablet-friendly screens."),
        ]
    )
    files = _compose(latest_preview=preview)
    requirements = _by_name(files)["requirements.md"]

    assert "## Other" in requirements
    assert "### Deployment Notes" in requirements
    assert "Technicians prefer tablet-friendly screens." in requirements


def test_sources_note_lists_source_ids_file_names_and_snippets():
    files = _compose(
        sources=[
            _source("SRC-000001", "repair workflow.pdf", "Repair workflow source"),
            _source("SRC-000002", "payment rules.txt", "Refund approval source"),
        ]
    )
    sources = _by_name(files)["sources.md"]

    assert "## Uploaded Sources" in sources
    assert "### SRC-000001 - repair workflow.pdf" in sources
    assert "Repair workflow source" in sources
    assert "### SRC-000002 - payment rules.txt" in sources
    assert "Refund approval source" in sources


def test_sources_note_handles_no_uploaded_sources():
    files = _compose(sources=[])

    assert "- No uploaded sources linked to the latest saved SAD." in _by_name(files)["sources.md"]


def test_index_lists_saved_sad_history_in_order():
    first = _save("SV-000001", "SP-000001", "doc-001", 1)
    second = _save("SV-000002", "SP-000002", "doc-002", 2)
    files = _compose(latest_save=second, all_saves_for_repo=[first, second])
    index = _by_name(files)["Wiki.md"]

    assert index.index("- SV-000001") < index.index("- SV-000002")


def test_compose_escapes_html_from_business_inputs():
    files = _compose(
        requirement_text="Track <b>repair</b> jobs.",
        sources=[_source("SRC-000001", "<script>bad</script>.pdf", "<bad>")],
    )
    markdown = "\n".join(file.markdown for file in files)

    assert "<b>" not in markdown
    assert "</b>" not in markdown
    assert "<script>" not in markdown
    assert "&lt;b&gt;repair&lt;/b&gt;" in markdown


def _compose(
    *,
    latest_save: SadSaveRecord | None = None,
    latest_preview: SadPreviewResponse | None = None,
    all_saves_for_repo: list[SadSaveRecord] | None = None,
    sources: list[SourceRecord] | None = None,
    requirement_text: str = "Repair shop wants to track jobs, parts, statuses, and payments.",
    composed_at: datetime | None = None,
):
    latest = latest_save or _save("SV-000002", "SP-000002", "doc-002", 2)
    return compose_wiki_files(
        repo=_repo(),
        latest_save=latest,
        latest_preview=latest_preview or _preview(),
        all_saves_for_repo=all_saves_for_repo
        or [
            _save("SV-000001", "SP-000001", "doc-001", 1),
            latest,
        ],
        sources=sources
        if sources is not None
        else [_source("SRC-000001", "repair workflow.pdf", "workflow")],
        requirement_text=requirement_text,
        composed_at=composed_at,
    )


def _by_name(files) -> dict[str, str]:
    return {file.name: file.markdown for file in files}


def _preview(
    sections: list[tuple[str, str]] | None = None,
) -> SadPreviewResponse:
    section_pairs = sections or [
        ("Goal and Scope", "Track repair jobs from drop-off through collection."),
        ("Users and Roles", "Counter staff create orders and technicians update repairs."),
        ("Access and Permissions", "Owners can override payment corrections."),
        ("Workflow Steps: Repair Handoffs", "Handoff from counter to technician to pickup desk."),
        ("Exceptions and Edge Cases", "Damaged parts and late pickups are flagged."),
        ("Data and Records", "Device, customer, parts, status, and payment records are stored."),
        ("Business Rules and Approvals", "Owner approval is required for refunds."),
        ("Non-functional Needs", "Staff login and audit history are required."),
        ("Reports and Summaries", "Daily owner summary shows open jobs."),
        ("Integrations", "No external integrations are needed in version one."),
    ]
    return SadPreviewResponse.model_validate(
        {
            "title": "Phone Repair SAD",
            "temporary_notice": "Temporary preview.",
            "it_readiness": {
                "label": "Layer 2",
                "score": 70,
                "confidence": "Medium",
                "checklist": [
                    {
                        "id": "data",
                        "label": "Data model",
                        "status": "needs_input",
                        "reason": "Detailed schema comes later.",
                    }
                ],
            },
            "sections": [
                {"title": title, "body": body, "source_references": ["SRC-000001"]}
                for title, body in section_pairs
            ],
            "assumptions": ["SMS notification wording can be finalized later."],
            "open_questions": ["Confirm who can waive diagnostic fees."],
            "source_references": ["SRC-000001"],
            "change_tracking": {
                "summary": "Initial preview.",
                "paths": ["requirements"],
            },
        }
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


def _source(source_id: str, filename: str, text: str) -> SourceRecord:
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
        extracted_text_preview=text,
        extracted_text=text,
        extraction_summary=f"{text} extracted",
        traceability_units=[],
        created_at=now,
        updated_at=now,
    )
