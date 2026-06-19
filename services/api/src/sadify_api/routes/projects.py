from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import JSONResponse

from sadify_api.config import ApiConfig, load_api_config
from sadify_api.routes.auth import verify_authorization_header
from sadify_api.schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectListResponse,
    ProjectSessionSnapshot,
    ProjectSavesResponse,
    ProjectSummary,
    SadSaveSummary,
    SetProjectGithubRequest,
    SwitchProjectRequest,
    SwitchProjectResponse,
)
from sadify_api.services.auth import TokenVerifier
from sadify_api.services.drive_client import (
    DriveClient,
    DriveFolderCreateError,
    DriveFolderTrashError,
    DriveTokenInvalidError,
)
from sadify_api.services.drive_repo import DriveRepoRepository
from sadify_api.services.github_issue_sets import (
    GithubIssueSetRepository,
    GithubIssueSetRepositoryProtocol,
)
from sadify_api.services.projects import (
    ProjectRepository,
    validate_github_repo,
    validate_project_name,
)
from sadify_api.services.sad_save import SadSaveRepository
from sadify_api.services.secret_store import SecretStore, get_secret_store
from sadify_api.services.session_state import SessionSnapshotRepository


def create_projects_router(
    drive_repo_repository: DriveRepoRepository,
    project_repository: ProjectRepository,
    sad_save_repository: SadSaveRepository,
    token_verifier: TokenVerifier,
    config: ApiConfig | None = None,
    drive_client: DriveClient | None = None,
    secret_store: SecretStore | None = None,
    session_snapshot_repository: SessionSnapshotRepository | None = None,
    github_issue_set_repository: GithubIssueSetRepositoryProtocol | None = None,
) -> APIRouter:
    config = config or load_api_config()
    session_snapshot_repository = (
        session_snapshot_repository or SessionSnapshotRepository()
    )
    github_issue_set_repository = (
        github_issue_set_repository or GithubIssueSetRepository()
    )
    router = APIRouter(prefix="/projects", tags=["projects"])

    @router.get("", response_model=ProjectListResponse)
    def list_projects(
        authorization: str | None = Header(default=None),
    ) -> ProjectListResponse:
        user = _verified_user(authorization, token_verifier)
        repo = _active_repo_or_error(drive_repo_repository, user.uid)
        projects = project_repository.list_projects(repo.grant_id)
        if config.drive_mode == "live":
            live_drive_client, access_token = _live_drive_context(
                config=config,
                drive_client=drive_client,
                secret_store=secret_store,
                owner_uid=user.uid,
            )
            try:
                folders = live_drive_client.list_subfolders(
                    access_token=access_token,
                    parent_folder_id=repo.repo_folder_id,
                )
            except DriveFolderCreateError as exc:
                raise _project_error(
                    502,
                    "PROJECT_FOLDER_LIST_FAILED",
                    "Could not list project folders in Drive.",
                ) from exc
            projects = project_repository.sync_from_drive(
                grant_id=repo.grant_id,
                drive_folders=folders,
            )
            drive_repo_repository.set_available_projects(
                grant_id=repo.grant_id,
                projects=projects,
            )
        return ProjectListResponse(
            active_project_id=repo.active_project_id,
            active_project_name=repo.active_project_name,
            projects=projects,
        )

    @router.post("", response_model=CreateProjectResponse)
    def create_project(
        request: CreateProjectRequest,
        authorization: str | None = Header(default=None),
    ) -> CreateProjectResponse:
        user = _verified_user(authorization, token_verifier)
        repo = _active_repo_or_error(drive_repo_repository, user.uid)
        try:
            name = validate_project_name(request.name)
        except ValueError as exc:
            raise _project_error(
                400,
                "PROJECT_NAME_INVALID",
                "Project name must be 1-80 chars, letters/numbers/spaces/underscores/hyphens.",
            ) from exc

        existing = project_repository.get_project_by_name(repo.grant_id, name)
        if existing is not None:
            project = existing
        elif config.drive_mode == "live":
            live_drive_client, access_token = _live_drive_context(
                config=config,
                drive_client=drive_client,
                secret_store=secret_store,
                owner_uid=user.uid,
            )
            try:
                folder = live_drive_client.find_or_create_folder(
                    access_token,
                    name,
                    parent_folder_id=repo.repo_folder_id,
                )
            except DriveFolderCreateError as exc:
                raise _project_error(
                    502,
                    "PROJECT_FOLDER_CREATE_FAILED",
                    "Could not create the project folder in Drive.",
                ) from exc
            project = project_repository.create_project(
                grant_id=repo.grant_id,
                name=name,
                drive_folder_id=folder.folder_id,
            )
        else:
            project = project_repository.create_local_project(
                grant_id=repo.grant_id,
                name=name,
            )

        drive_repo_repository.set_active_project(
            grant_id=repo.grant_id,
            project=project,
        )
        return CreateProjectResponse(
            project=project,
            active_project_id=project.project_id,
        )

    @router.get("/{project_id}/saves", response_model=ProjectSavesResponse)
    def list_project_saves(
        project_id: str,
        authorization: str | None = Header(default=None),
    ) -> ProjectSavesResponse:
        user = _verified_history_user(authorization, token_verifier)
        repo = _active_repo_for_history_or_error(drive_repo_repository, user.uid)
        project = project_repository.get_project(repo.grant_id, project_id)
        if project is None:
            raise _project_error(
                404,
                "PROJECT_NOT_FOUND",
                "Project not found in this Drive repo.",
            )
        records = sad_save_repository.list_for_project(
            grant_id=repo.grant_id,
            project_id=project.project_id,
        )
        prepared_save_ids = {
            issue_set.save_id
            for issue_set in github_issue_set_repository.list_for_project(
                repo.grant_id,
                project.project_id,
            )
        }
        return ProjectSavesResponse(
            project_id=project.project_id,
            project_name=project.name,
            saves=[
                SadSaveSummary(
                    save_id=record.save_id,
                    preview_id=record.preview_id,
                    doc_url=record.sad_doc.url,
                    doc_path=record.sad_doc.path,
                    title=record.sad_doc.title,
                    change_summary=record.change_summary,
                    source_ids=[
                        artifact.source_ids[0]
                        for artifact in record.source_artifact_references
                        if artifact.source_ids
                    ],
                    created_at=record.created_at,
                    has_github_issue_set=record.save_id in prepared_save_ids,
                )
                for record in records
            ],
        )

    @router.put("/{project_id}/session", status_code=204)
    def put_project_session(
        project_id: str,
        snapshot: ProjectSessionSnapshot,
        authorization: str | None = Header(default=None),
    ) -> Response:
        user = _verified_user(authorization, token_verifier)
        repo = _active_repo_or_error(drive_repo_repository, user.uid)
        if project_repository.get_project(repo.grant_id, project_id) is None:
            raise _project_error(
                404,
                "PROJECT_NOT_FOUND",
                "Project not found in this Drive repo.",
            )
        session_snapshot_repository.upsert(repo.grant_id, project_id, snapshot)
        return Response(status_code=204)

    @router.get("/{project_id}/session")
    def get_project_session(
        project_id: str,
        authorization: str | None = Header(default=None),
    ) -> Response:
        user = _verified_user(authorization, token_verifier)
        repo = _active_repo_or_error(drive_repo_repository, user.uid)
        if project_repository.get_project(repo.grant_id, project_id) is None:
            raise _project_error(
                404,
                "PROJECT_NOT_FOUND",
                "Project not found in this Drive repo.",
            )
        snapshot = session_snapshot_repository.get(repo.grant_id, project_id)
        if snapshot is None:
            return Response(status_code=204)
        return JSONResponse(content=snapshot.model_dump(mode="json"))

    @router.delete("/{project_id}", response_model=ProjectListResponse)
    def delete_project(
        project_id: str,
        authorization: str | None = Header(default=None),
    ) -> ProjectListResponse:
        user = _verified_user(authorization, token_verifier)
        repo = _active_repo_or_error(drive_repo_repository, user.uid)
        project = project_repository.get_project(repo.grant_id, project_id)
        if project is None:
            raise _project_error(
                404,
                "PROJECT_NOT_FOUND",
                "Project not found in this Drive repo.",
            )

        if config.drive_mode == "live" and not project.drive_folder_id.startswith(
            "LOCAL-"
        ):
            live_drive_client, access_token = _live_drive_context(
                config=config,
                drive_client=drive_client,
                secret_store=secret_store,
                owner_uid=user.uid,
            )
            try:
                live_drive_client.trash_folder(
                    access_token,
                    project.drive_folder_id,
                )
            except DriveFolderTrashError as exc:
                raise _project_error(
                    502,
                    "PROJECT_DELETE_DRIVE_FAILED",
                    "Could not move the project folder to Drive Trash.",
                ) from exc

        try:
            sad_save_repository.delete_for_project(repo.grant_id, project_id)
            session_snapshot_repository.delete(repo.grant_id, project_id)
            github_issue_set_repository.delete_for_project(repo.grant_id, project_id)
            project_repository.delete_project(repo.grant_id, project_id)
        except Exception as exc:
            raise _project_error(
                502,
                "PROJECT_DELETE_FAILED",
                "Could not finish deleting the project; retry.",
            ) from exc

        drive_repo_repository.clear_active_project(repo.grant_id, project_id)
        projects = project_repository.list_projects(repo.grant_id)
        drive_repo_repository.set_available_projects(
            grant_id=repo.grant_id,
            projects=projects,
        )
        refreshed = drive_repo_repository.get_active_repo(user.uid)
        return ProjectListResponse(
            active_project_id=(refreshed.active_project_id if refreshed else None),
            active_project_name=(refreshed.active_project_name if refreshed else None),
            projects=projects,
        )

    @router.post("/{project_id}/github", response_model=ProjectSummary)
    def link_github_repo(
        project_id: str,
        request: SetProjectGithubRequest,
        authorization: str | None = Header(default=None),
    ) -> ProjectSummary:
        user = _verified_user(authorization, token_verifier)
        repo = _active_repo_or_error(drive_repo_repository, user.uid)
        project = project_repository.get_project(repo.grant_id, project_id)
        if project is None:
            raise _project_error(
                404,
                "PROJECT_NOT_FOUND",
                "Project not found in this Drive repo.",
            )
        try:
            github_repo = validate_github_repo(request.repo)
        except ValueError as exc:
            raise _project_error(
                422,
                "GITHUB_REPO_INVALID",
                "Enter your repository as owner/name (e.g. octocat/hello-world).",
            ) from exc
        updated = project_repository.set_github_repo(
            repo.grant_id, project.project_id, github_repo
        )
        if updated is None:
            raise _project_error(
                404,
                "PROJECT_NOT_FOUND",
                "Project not found in this Drive repo.",
            )
        return updated

    @router.post("/switch", response_model=SwitchProjectResponse)
    def switch_project(
        request: SwitchProjectRequest,
        authorization: str | None = Header(default=None),
    ) -> SwitchProjectResponse:
        user = _verified_user(authorization, token_verifier)
        repo = _active_repo_or_error(drive_repo_repository, user.uid)
        project = project_repository.get_project(repo.grant_id, request.project_id)
        if project is None:
            raise _project_error(
                404,
                "PROJECT_NOT_FOUND",
                "Project not found in this Drive repo.",
            )
        drive_repo_repository.set_active_project(
            grant_id=repo.grant_id,
            project=project,
        )
        return SwitchProjectResponse(
            active_project_id=project.project_id,
            active_project_name=project.name,
        )

    return router


def _verified_user(authorization: str | None, token_verifier: TokenVerifier):
    try:
        return verify_authorization_header(authorization, token_verifier)
    except HTTPException as exc:
        if exc.status_code == 401:
            raise _project_error(
                401,
                "PROJECT_AUTH_REQUIRED",
                "Sign in before managing projects.",
            ) from exc
        raise


def _verified_history_user(authorization: str | None, token_verifier: TokenVerifier):
    try:
        return verify_authorization_header(authorization, token_verifier)
    except HTTPException as exc:
        if exc.status_code == 401:
            raise _project_error(
                401,
                "PROJECT_AUTH_REQUIRED",
                "Sign in to view project history.",
            ) from exc
        raise


def _active_repo_or_error(
    drive_repo_repository: DriveRepoRepository,
    owner_uid: str,
):
    repo = drive_repo_repository.get_active_repo(owner_uid)
    if repo is None:
        latest_repo = drive_repo_repository.get_latest_repo(owner_uid)
        if latest_repo and (
            latest_repo.status == "disconnected" or latest_repo.saves_blocked
        ):
            raise _project_error(
                409,
                "PROJECT_REPO_DISCONNECTED",
                "Reconnect Google Drive.",
            )
        raise _project_error(
            409,
            "PROJECT_REPO_REQUIRED",
            "Connect a Google Drive project repo before managing projects.",
        )
    if repo.status == "disconnected" or repo.saves_blocked:
        raise _project_error(
            409,
            "PROJECT_REPO_DISCONNECTED",
            "Reconnect Google Drive.",
        )
    return repo


def _active_repo_for_history_or_error(
    drive_repo_repository: DriveRepoRepository,
    owner_uid: str,
):
    repo = drive_repo_repository.get_active_repo(owner_uid)
    if repo is None:
        latest_repo = drive_repo_repository.get_latest_repo(owner_uid)
        if latest_repo and (
            latest_repo.status == "disconnected" or latest_repo.saves_blocked
        ):
            raise _project_error(
                409,
                "PROJECT_REPO_DISCONNECTED",
                "Reconnect Google Drive to view project history.",
            )
        raise _project_error(
            409,
            "PROJECT_REPO_REQUIRED",
            "Connect a Google Drive project repo first.",
        )
    if repo.status == "disconnected" or repo.saves_blocked:
        raise _project_error(
            409,
            "PROJECT_REPO_DISCONNECTED",
            "Reconnect Google Drive to view project history.",
        )
    return repo


def _live_drive_context(
    *,
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
    owner_uid: str,
) -> tuple[DriveClient, str]:
    if not config.drive_live_enabled:
        raise _project_error(
            503,
            "PROJECT_LIVE_MODE_DISABLED",
            "Live project Drive access is disabled for this process.",
        )
    resolved_secret_store = secret_store or get_secret_store(
        project_id=config.google_cloud_project,
        oauth_client_secret_name=config.google_oauth_client_secret_name,
    )
    resolved_drive_client = drive_client or DriveClient(
        client_id=config.google_oauth_client_id,
        client_secret=resolved_secret_store.get_oauth_client_secret(),
    )
    refresh_token = resolved_secret_store.get_user_refresh_token(owner_uid)
    if not refresh_token:
        raise _project_error(
            409,
            "PROJECT_REPO_DISCONNECTED",
            "Reconnect Google Drive.",
        )
    try:
        access_token = resolved_drive_client.refresh_access_token(refresh_token)
    except DriveTokenInvalidError as exc:
        raise _project_error(
            409,
            "PROJECT_REPO_DISCONNECTED",
            "Reconnect Google Drive.",
        ) from exc
    return resolved_drive_client, access_token


def _project_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
