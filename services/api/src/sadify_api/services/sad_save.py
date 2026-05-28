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
from sadify_api.services.drive_client import (
    DriveClient,
    DriveTokenInvalidError,
    DriveUploadError,
)
from sadify_api.services.sad_markdown import compose_sad_markdown
from sadify_api.services.secret_store import SecretStore


class SadSaveTokenMissingError(Exception):
    pass


class SadSaveTokenInvalidError(Exception):
    pass


class SadSaveDriveUploadError(Exception):
    pass


class SadSaveRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], SadSaveRecord] = {}
        self._by_idempotency_key: dict[str, tuple[str, str, str]] = {}
        self._counters: dict[tuple[str, str, str], int] = {}
        self._next_fake_doc_number = 1

    def save_preview(
        self,
        *,
        owner_uid: str,
        owner_email: str | None,
        repo: DriveRepoRecord,
        project_id: str | None = None,
        preview_record: SadPreviewRecord,
        sources: list[SourceRecord],
        saved_at: datetime | None = None,
        mode: str = "local",
        drive_client: DriveClient | None = None,
        secret_store: SecretStore | None = None,
        target_folder_id: str | None = None,
    ) -> SadSaveRecord:
        now = saved_at or datetime.now(UTC)
        effective_project_id = project_id or repo.active_project_id or repo.project_id
        preview_revision = preview_record.created_at.isoformat()
        idempotency_key = _idempotency_key(
            owner_uid=owner_uid,
            repo_grant_id=repo.grant_id,
            project_id=effective_project_id,
            preview_id=preview_record.preview_id,
            preview_revision=preview_revision,
        )
        existing_key = self._by_idempotency_key.get(idempotency_key)
        if existing_key:
            return self._records[existing_key]

        save_id = f"SV-{self._next_number(repo.grant_id, effective_project_id, 'sad_save'):06d}"
        manifest_id = f"SM-{self._next_number(repo.grant_id, effective_project_id, 'manifest'):06d}"
        source_ids = [source.source_id for source in sources]
        sad_doc = self._sad_doc_artifact(
            artifact_id=self._next_artifact_id(repo.grant_id, effective_project_id),
            save_id=save_id,
            preview_record=preview_record,
            source_ids=source_ids,
            created_at=now,
        )
        source_artifacts = [
            self._source_artifact(
                artifact_id=self._next_artifact_id(repo.grant_id, effective_project_id),
                source=source,
                created_at=now,
            )
            for source in sources
        ]
        manifest_artifact = self._generic_artifact(
            artifact_id=self._next_artifact_id(repo.grant_id, effective_project_id),
            artifact_type="manifest",
            title=f"_SADify manifest for {save_id}",
            path=f"_SADify/manifest-{save_id}.json",
            mime_type="application/json",
            created_at=now,
        )
        change_log_artifact = self._generic_artifact(
            artifact_id=self._next_artifact_id(repo.grant_id, effective_project_id),
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
            project_id=effective_project_id,
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
        if mode == "live":
            record = self._with_live_drive_artifact(
                record=record,
                repo=repo,
                owner_uid=owner_uid,
                preview_record=preview_record,
                drive_client=drive_client,
                secret_store=secret_store,
                updated_at=now,
                target_folder_id=target_folder_id,
            )

        record_key = (repo.grant_id, effective_project_id, save_id)
        self._records[record_key] = record
        self._by_idempotency_key[idempotency_key] = record_key
        return record

    def _with_live_drive_artifact(
        self,
        *,
        record: SadSaveRecord,
        repo: DriveRepoRecord,
        owner_uid: str,
        preview_record: SadPreviewRecord,
        drive_client: DriveClient | None,
        secret_store: SecretStore | None,
        updated_at: datetime,
        target_folder_id: str | None,
    ) -> SadSaveRecord:
        if drive_client is None or secret_store is None:
            raise SadSaveTokenMissingError("Live Drive dependencies are not configured.")
        refresh_token = secret_store.get_user_refresh_token(owner_uid)
        if not refresh_token:
            raise SadSaveTokenMissingError("Drive refresh token is missing.")
        try:
            access_token = drive_client.refresh_access_token(refresh_token)
        except DriveTokenInvalidError as exc:
            raise SadSaveTokenInvalidError(
                "Drive refresh token is invalid or expired."
            ) from exc
        try:
            upload = drive_client.upload_markdown_as_doc(
                access_token=access_token,
                folder_id=target_folder_id or repo.repo_folder_id,
                title=preview_record.preview.title,
                markdown=compose_sad_markdown(preview_record.preview),
            )
        except DriveUploadError as exc:
            raise SadSaveDriveUploadError("Google Drive rejected the upload.") from exc

        sad_doc = record.sad_doc.model_copy(
            update={
                "file_id": upload.file_id,
                "url": upload.web_view_link,
            }
        )
        artifacts = [
            sad_doc if artifact.artifact_id == record.sad_doc.artifact_id else artifact
            for artifact in record.artifacts
        ]
        return record.model_copy(
            update={
                "sad_doc": sad_doc,
                "artifacts": artifacts,
                "change_summary": (
                    f"SAD preview {preview_record.preview_id} saved to "
                    f"{repo.repo_folder_name} as Google Doc {upload.web_view_link}."
                ),
                "updated_at": updated_at,
            }
        )

    def get_save(
        self,
        save_id: str,
        *,
        repo_grant_id: str | None = None,
        project_id: str | None = None,
    ) -> SadSaveRecord | None:
        if repo_grant_id is not None and project_id is not None:
            return self._records.get((repo_grant_id, project_id, save_id))
        for (grant_id, stored_project_id, stored_save_id), record in self._records.items():
            if stored_save_id != save_id:
                continue
            if repo_grant_id is not None and grant_id != repo_grant_id:
                continue
            if project_id is not None and stored_project_id != project_id:
                continue
            return record
        return None

    def record_count(self) -> int:
        return len(self._records)

    def _sad_doc_artifact(
        self,
        *,
        artifact_id: str,
        save_id: str,
        preview_record: SadPreviewRecord,
        source_ids: list[str],
        created_at: datetime,
    ) -> SadSaveArtifact:
        fake_doc_id = f"LOCAL-GDOC-{self._next_fake_doc_number:06d}"
        self._next_fake_doc_number += 1
        return self._artifact(
            artifact_id=artifact_id,
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
        artifact_id: str,
        source: SourceRecord,
        created_at: datetime,
    ) -> SadSaveArtifact:
        safe_name = _safe_path_part(source.original_file_name)
        return self._artifact(
            artifact_id=artifact_id,
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
        artifact_id: str,
        artifact_type: str,
        title: str,
        path: str,
        mime_type: str,
        created_at: datetime,
    ) -> SadSaveArtifact:
        return self._artifact(
            artifact_id=artifact_id,
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
        artifact_id: str,
        artifact_type: str,
        title: str,
        path: str,
        file_id: str | None,
        url: str | None,
        mime_type: str | None,
        source_ids: list[str],
        created_at: datetime,
    ) -> SadSaveArtifact:
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

    def _next_artifact_id(self, grant_id: str, project_id: str) -> str:
        return f"SA-{self._next_number(grant_id, project_id, 'artifact'):06d}"

    def _next_number(self, grant_id: str, project_id: str, counter_name: str) -> int:
        key = (grant_id, project_id, counter_name)
        value = self._counters.get(key, 1)
        self._counters[key] = value + 1
        return value


def _idempotency_key(
    *,
    owner_uid: str,
    repo_grant_id: str,
    project_id: str,
    preview_id: str,
    preview_revision: str,
) -> str:
    return "|".join(
        [owner_uid, repo_grant_id, project_id, preview_id, preview_revision]
    )


def _safe_path_part(value: str) -> str:
    clean = value.replace("/", "-").replace("\\", "-").strip()
    clean = re.sub(r"\s+", "-", clean)
    return clean or "source"


_sad_save_repository = SadSaveRepository()


def get_sad_save_repository() -> SadSaveRepository:
    return _sad_save_repository
