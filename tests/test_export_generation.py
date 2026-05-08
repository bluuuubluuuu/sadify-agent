from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document
from pypdf import PdfReader

from sadify.renderers.wiki_markdown import render_wiki_notes
from sadify.services.export_generation import (
    ExportGenerationError,
    ExportPackage,
    PreparedExportArtifact,
    prepare_export_package,
    write_export_package,
)
from sadify.services.relationship_linking import build_requirement_graph
from sadify.services.sad_generation import generate_project_sad


TIMESTAMP = datetime(2026, 5, 8, tzinfo=timezone.utc)


def test_prepare_export_package_creates_sad_document_artifacts_and_records():
    sad, notes = _sample_sad_and_notes()

    package = prepare_export_package(
        sad_version=sad,
        wiki_notes=notes,
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    assert package.export_types()[:3] == ("google_doc", "pdf", "docx")
    assert package.artifact_by_type("google_doc").relative_path.startswith("sad/")
    assert package.artifact_by_type("pdf").content.startswith(b"%PDF-")
    assert package.artifact_by_type("docx").content.startswith(b"PK")
    assert [record.export_id for record in package.records[:3]] == [
        "EXP-001",
        "EXP-002",
        "EXP-003",
    ]
    assert all(record.source_sad_version_id == "SAD-001" for record in package.records)
    assert all(record.status == "success" for record in package.records)
    assert all(record.drive_file_id is None for record in package.records)


def test_pdf_and_docx_artifacts_are_readable():
    sad, notes = _sample_sad_and_notes()
    package = prepare_export_package(
        sad_version=sad,
        wiki_notes=notes,
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    pdf = package.artifact_by_type("pdf")
    reader = PdfReader(BytesIO(pdf.content))
    assert len(reader.pages) == 1

    docx = package.artifact_by_type("docx")
    document = Document(BytesIO(docx.content))
    paragraph_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Warehouse Operations System Analysis And Design" in paragraph_text
    assert "Source Traceability" in paragraph_text


def test_wiki_markdown_artifacts_keep_note_paths_and_content():
    sad, notes = _sample_sad_and_notes()
    package = prepare_export_package(
        sad_version=sad,
        wiki_notes=notes,
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    requirement_note = next(note for note in notes if note.item_id == "REQ-001")
    artifact = package.artifact_by_relative_path(
        f"wiki/{requirement_note.relative_path}"
    )

    assert artifact.export_type == "wiki_markdown"
    assert artifact.content.decode("utf-8") == requirement_note.markdown


def test_write_export_package_materializes_relative_paths():
    sad, notes = _sample_sad_and_notes()
    package = prepare_export_package(
        sad_version=sad,
        wiki_notes=notes[:1],
        project_slug="warehouse-operations",
        created_at=TIMESTAMP,
        created_by="local-user",
    )

    output_dir = _local_temp_path()
    written_paths = write_export_package(package, output_dir)

    assert len(written_paths) == len(package.artifacts)
    assert all(path.exists() for path in written_paths)
    assert all(
        output_dir.resolve() in path.resolve().parents for path in written_paths
    )


def test_write_export_package_rejects_paths_outside_target():
    artifact = PreparedExportArtifact(
        export_id="EXP-999",
        export_type="wiki_markdown",
        relative_path="../escape.md",
        file_name="escape.md",
        mime_type="text/markdown",
        content=b"escape",
    )
    package = ExportPackage(artifacts=(artifact,), records=())

    with pytest.raises(ExportGenerationError):
        write_export_package(package, _local_temp_path())


def _sample_sad_and_notes():
    graph = build_requirement_graph(
        requirement_id="REQ-001",
        title="Warehouse Stock Movement",
        requirement_text=(
            "Warehouse operators scan stock during receiving, picking, packing, "
            "and dispatch. They record item code, quantity, location, date, "
            "status, and remarks. Supervisors approve rejected records. "
            "Managers need daily dashboards and weekly exports. The system "
            "needs role-based access and audit history."
        ),
        source_ids=("SRC-001",),
        created_at=TIMESTAMP,
    )
    sad = generate_project_sad(
        sad_version_id="SAD-001",
        project_title="Warehouse Operations",
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
        created_at=TIMESTAMP,
        created_by="local-user",
    )
    notes = render_wiki_notes(
        knowledge_items=graph.knowledge_items,
        relationships=graph.relationships,
    )
    return sad, notes


def _local_temp_path():
    base_dir = Path("tmp") / "test-export-generation"
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path
