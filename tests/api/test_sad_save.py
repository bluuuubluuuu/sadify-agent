from fastapi.testclient import TestClient

from sadify.extractors.business_files import ExtractedRequirementSource
from sadify_api.main import create_app
from sadify_api.schemas import SadPreviewResponse
from sadify_api.services.auth import VerifiedFirebaseUser
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.sad_preview import SadPreviewRepository
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.source_uploads import SourceRepository
from tests.api.test_sad_preview import VALID_PREVIEW


class AcceptingTokenVerifier:
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        return VerifiedFirebaseUser(
            uid="firebase-uid-001",
            email="owner@example.com",
            display_name="Project Owner",
            provider="firebase",
        )


def test_sad_save_success_creates_local_artifacts():
    client, drive_repo, preview_repo, save_repo, _source_repo = _client_with_repos()
    _connect_repo(client)
    preview_record = _save_preview(preview_repo)

    response = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": preview_record.preview_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["message"] == "SAD preview saved to the local project repo record."
    record = payload["record"]
    assert record["save_id"] == "SV-000001"
    assert record["preview_id"] == "SP-000001"
    assert record["repo_grant_id"] == "DG-000001"
    assert record["repo_folder_name"] == "Operations MVP"
    assert record["sad_doc"]["artifact_type"] == "google_doc"
    assert record["sad_doc"]["file_id"] == "LOCAL-GDOC-000001"
    assert (
        record["sad_doc"]["url"]
        == "https://docs.google.com/document/d/LOCAL-GDOC-000001/edit"
    )
    assert record["sad_doc"]["path"].startswith("SAD/")
    assert any(
        path.startswith("SAD/") for path in record["manifest"]["artifact_paths"]
    )
    assert any(
        path.startswith("_SADify/manifest")
        for path in record["manifest"]["artifact_paths"]
    )
    assert any(
        path.startswith("_SADify/change-log")
        for path in record["manifest"]["artifact_paths"]
    )
    assert "SP-000001" in record["change_summary"]
    assert "Operations MVP" in record["change_summary"]
    assert save_repo.get_save("SV-000001") is not None
    assert drive_repo.get_active_repo("firebase-uid-001") is not None


def test_sad_save_requires_signed_in_user():
    client, _drive_repo, preview_repo, _save_repo, _source_repo = _client_with_repos()
    preview_record = _save_preview(preview_repo)

    response = client.post(
        "/sad/save",
        json={"preview_id": preview_record.preview_id},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "SAD_SAVE_AUTH_REQUIRED",
        "message": "Sign in before saving the SAD preview.",
    }


def test_sad_save_blocks_without_active_repo():
    client, _drive_repo, preview_repo, _save_repo, _source_repo = _client_with_repos()
    preview_record = _save_preview(preview_repo)

    response = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": preview_record.preview_id},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SAD_SAVE_REPO_REQUIRED"


def test_sad_save_blocks_disconnected_repo():
    client, drive_repo, preview_repo, _save_repo, _source_repo = _client_with_repos()
    _connect_repo(client)
    client.post("/drive/repo/disconnect", headers=_auth_header())
    preview_record = _save_preview(preview_repo)

    response = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": preview_record.preview_id},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SAD_SAVE_REPO_DISCONNECTED"
    latest = drive_repo.get_latest_repo("firebase-uid-001")
    assert latest is not None
    assert latest.status == "disconnected"
    assert latest.saves_blocked is True


def test_sad_save_requires_preview_id():
    client, _drive_repo, _preview_repo, _save_repo, _source_repo = _client_with_repos()
    _connect_repo(client)

    response = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "SAD_SAVE_PREVIEW_REQUIRED"


def test_sad_save_rejects_unknown_preview_id():
    client, _drive_repo, _preview_repo, _save_repo, _source_repo = _client_with_repos()
    _connect_repo(client)

    response = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": "SP-999999"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SAD_SAVE_PREVIEW_NOT_FOUND"


def test_sad_save_is_idempotent_for_same_preview_revision():
    client, _drive_repo, preview_repo, save_repo, _source_repo = _client_with_repos()
    _connect_repo(client)
    preview_record = _save_preview(preview_repo)

    first = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": preview_record.preview_id},
    )
    second = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": preview_record.preview_id},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_record = first.json()["record"]
    second_record = second.json()["record"]
    assert first_record["save_id"] == second_record["save_id"]
    assert first_record["sad_doc"]["file_id"] == second_record["sad_doc"]["file_id"]
    assert save_repo.record_count() == 1


def test_sad_save_includes_uploaded_source_refs_when_sources_exist():
    client, _drive_repo, preview_repo, _save_repo, source_repo = _client_with_repos()
    _connect_repo(client)
    source = source_repo.save_extracted_source(
        extracted=ExtractedRequirementSource(
            filename="laundry workflow.pdf",
            file_type="pdf",
            normalized_text="Laundry shop workflow source text.",
            metadata={"byte_count": 128, "page_count": 1},
        ),
        mime_type="application/pdf",
    )
    preview_record = _save_preview(preview_repo, source_references=[source.source_id])

    response = client.post(
        "/sad/save",
        headers=_auth_header(),
        json={"preview_id": preview_record.preview_id},
    )

    assert response.status_code == 200
    record = response.json()["record"]
    assert record["manifest"]["source_ids"] == ["SRC-000001"]
    assert len(record["source_artifact_references"]) == 1
    source_artifact = record["source_artifact_references"][0]
    assert source_artifact["artifact_type"] == "source_reference"
    assert source_artifact["source_ids"] == ["SRC-000001"]
    assert source_artifact["path"].startswith("Sources/")


def _client_with_repos():
    drive_repo = DriveRepoRepository()
    preview_repo = SadPreviewRepository()
    save_repo = SadSaveRepository()
    source_repo = SourceRepository()
    client = TestClient(
        create_app(
            token_verifier=AcceptingTokenVerifier(),
            drive_repo_repository=drive_repo,
            sad_preview_repository=preview_repo,
            sad_save_repository=save_repo,
            source_repository=source_repo,
        )
    )
    return client, drive_repo, preview_repo, save_repo, source_repo


def _connect_repo(client: TestClient):
    response = client.post(
        "/drive/repo/connect",
        headers=_auth_header(),
        json={
            "project_id": "PROJ-000001",
            "authorization_code": "mock-authorization-code",
            "repo_folder_name": "Operations MVP",
            "create_new_repo": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def _save_preview(
    preview_repo: SadPreviewRepository,
    *,
    source_references: list[str] | None = None,
):
    preview_payload = {
        **VALID_PREVIEW,
        "source_references": source_references or [],
        "sections": [
            {
                **section,
                "source_references": source_references or [],
            }
            for section in VALID_PREVIEW["sections"]
        ],
    }
    return preview_repo.save_preview(
        requirement_text="Need to validate an operational workflow.",
        analysis_id="AN-000001",
        preview=SadPreviewResponse.model_validate(preview_payload),
    )


def _auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer firebase-test-token"}
