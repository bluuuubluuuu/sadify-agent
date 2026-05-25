from datetime import UTC, datetime
import re

from sadify_api.schemas import (
    DriveRepoRecord,
    SadPreviewRecord,
    SadSaveArtifact,
    SadSaveManifest,
    SadSaveRecord,
    SourceRecord,
)


class SadSaveRepository:
    def __init__(self) -> None:
        self._records: dict[str, SadSaveRecord] = {}
        self._by_idempotency_key: dict[str, str] = {}
        self._next_save_number = 1
        self._next_artifact_number = 1
        self._next_manifest_number = 1
        self._next_fake_doc_number = 1

    def save_preview(
        self,
        *,
        owner_uid: str,
        owner_email: str | None,
        repo: DriveRepoRecord,
        preview_record: SadPreviewRecord,
        sources: list[SourceRecord],
        saved_at: datetime | None = None,
    ) -> SadSaveRecord:
        now = saved_at or datetime.now(UTC)
        preview_revision = preview_record.created_at.isoformat()
        idempotency_key = _idempotency_key(
            owner_uid=owner_uid,
            repo_grant_id=repo.grant_id,
            preview_id=preview_record.preview_id,
            preview_revision=preview_revision,
        )
        existing_save_id = self._by_idempotency_key.get(idempotency_key)
        if existing_save_id:
            return self._records[existing_save_id]

        save_id = f"SV-{self._next_save_number:06d}"
        self._next_save_number += 1
        manifest_id = f"SM-{self._next_manifest_number:06d}"
        self._next_manifest_number += 1
        source_ids = [source.source_id for source in sources]
        sad_doc = self._sad_doc_artifact(
            save_id=save_id,
            preview_record=preview_record,
            source_ids=source_ids,
            created_at=now,
        )
        source_artifacts = [
            self._source_artifact(source=source, created_at=now)
            for source in sources
        ]
        manifest_artifact = self._generic_artifact(
            artifact_type="manifest",
            title=f"_SADify manifest for {save_id}",
            path=f"_SADify/manifest-{save_id}.json",
            mime_type="application/json",
            created_at=now,
        )
        change_log_artifact = self._generic_artifact(
            artifact_type="change_log",
            title=f"_SADify change log for {save_id}",
            path=f"_SADify/change-log-{save_id}.json",
            mime_type="application/json",
            created_at=now,
        )
        artifacts = [
            sad_doc,
            manifest_artifact,
            change_log_artifact,
            *source_artifacts,
        ]
        manifest = SadSaveManifest(
            manifest_id=manifest_id,
            repo_grant_id=repo.grant_id,
            repo_folder_id=repo.repo_folder_id,
            repo_folder_name=repo.repo_folder_name,
            preview_id=preview_record.preview_id,
            preview_revision=preview_revision,
            analysis_id=preview_record.analysis_id,
            requirement_text=preview_record.requirement_text,
            sad_title=preview_record.preview.title,
            preview_section_count=len(preview_record.preview.sections),
            preview_assumption_count=len(preview_record.preview.assumptions),
            preview_open_question_count=len(preview_record.preview.open_questions),
            preview_source_references=list(preview_record.preview.source_references),
            source_ids=source_ids,
            artifact_paths=[artifact.path for artifact in artifacts],
            saved_at=now,
        )
        record = SadSaveRecord(
            save_id=save_id,
            idempotency_key=idempotency_key,
            owner_uid=owner_uid,
            owner_email=owner_email,
            project_id=repo.project_id,
            repo_grant_id=repo.grant_id,
            repo_folder_id=repo.repo_folder_id,
            repo_folder_name=repo.repo_folder_name,
            preview_id=preview_record.preview_id,
            preview_revision=preview_revision,
            status="saved",
            sad_doc=sad_doc,
            artifacts=artifacts,
            manifest=manifest,
            change_summary=(
                f"SAD preview {preview_record.preview_id} saved to "
                f"{repo.repo_folder_name} as {sad_doc.path}."
            ),
            source_artifact_references=source_artifacts,
            created_at=now,
            updated_at=now,
        )
        self._records[save_id] = record
        self._by_idempotency_key[idempotency_key] = save_id
        return record

    def get_save(self, save_id: str) -> SadSaveRecord | None:
        return self._records.get(save_id)

    def record_count(self) -> int:
        return len(self._records)

    def _sad_doc_artifact(
        self,
        *,
        save_id: str,
        preview_record: SadPreviewRecord,
        source_ids: list[str],
        created_at: datetime,
    ) -> SadSaveArtifact:
        fake_doc_id = f"LOCAL-GDOC-{self._next_fake_doc_number:06d}"
        self._next_fake_doc_number += 1
        return self._artifact(
            artifact_type="google_doc",
            title=preview_record.preview.title,
            path=f"SAD/SAD-{preview_record.preview_id}-{save_id}.google_doc",
            file_id=fake_doc_id,
            url=f"https://docs.google.com/document/d/{fake_doc_id}/edit",
            mime_type="application/vnd.google-apps.document",
            source_ids=source_ids,
            created_at=created_at,
        )

    def _source_artifact(
        self,
        *,
        source: SourceRecord,
        created_at: datetime,
    ) -> SadSaveArtifact:
        safe_name = _safe_path_part(source.original_file_name)
        return self._artifact(
            artifact_type="source_reference",
            title=f"Source reference {source.source_id}: {source.original_file_name}",
            path=f"Sources/{source.source_id}-{safe_name}.source-ref.json",
            file_id=None,
            url=None,
            mime_type="application/json",
            source_ids=[source.source_id],
            created_at=created_at,
        )

    def _generic_artifact(
        self,
        *,
        artifact_type: str,
        title: str,
        path: str,
        mime_type: str,
        created_at: datetime,
    ) -> SadSaveArtifact:
        return self._artifact(
            artifact_type=artifact_type,
            title=title,
            path=path,
            file_id=None,
            url=None,
            mime_type=mime_type,
            source_ids=[],
            created_at=created_at,
        )

    def _artifact(
        self,
        *,
        artifact_type: str,
        title: str,
        path: str,
        file_id: str | None,
        url: str | None,
        mime_type: str | None,
        source_ids: list[str],
        created_at: datetime,
    ) -> SadSaveArtifact:
        artifact_id = f"SA-{self._next_artifact_number:06d}"
        self._next_artifact_number += 1
        return SadSaveArtifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            title=title,
            path=path,
            file_id=file_id,
            url=url,
            mime_type=mime_type,
            source_ids=source_ids,
            created_at=created_at,
        )


def _idempotency_key(
    *,
    owner_uid: str,
    repo_grant_id: str,
    preview_id: str,
    preview_revision: str,
) -> str:
    return "|".join([owner_uid, repo_grant_id, preview_id, preview_revision])


def _safe_path_part(value: str) -> str:
    clean = value.replace("/", "-").replace("\\", "-").strip()
    clean = re.sub(r"\s+", "-", clean)
    return clean or "source"


_sad_save_repository = SadSaveRepository()


def get_sad_save_repository() -> SadSaveRepository:
    return _sad_save_repository
