from __future__ import annotations

import os

os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseUpload


TOKEN_URI = "https://oauth2.googleapis.com/token"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"


class DriveOauthExchangeError(Exception):
    pass


class DriveTokenInvalidError(Exception):
    pass


class DriveFolderCreateError(Exception):
    pass


class DriveUploadError(Exception):
    pass


class DriveTextFileError(Exception):
    pass


@dataclass(frozen=True)
class DriveTokens:
    access_token: str
    refresh_token: str
    expiry: datetime | None


@dataclass(frozen=True)
class DriveFolder:
    folder_id: str
    name: str


@dataclass(frozen=True)
class DriveFolderRef:
    folder_id: str
    name: str
    created_time: datetime
    web_view_link: str | None


@dataclass(frozen=True)
class DriveUploadResult:
    file_id: str
    web_view_link: str


@dataclass(frozen=True)
class DriveFileRef:
    file_id: str
    name: str
    mime_type: str | None
    web_view_link: str | None
    md5_checksum: str | None


class DriveClient:
    def __init__(self, *, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret

    def exchange_authorization_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> DriveTokens:
        flow = Flow.from_client_config(
            _client_config(self.client_id, self.client_secret),
            scopes=[DRIVE_FILE_SCOPE],
            redirect_uri=redirect_uri,
        )
        try:
            flow.fetch_token(code=code)
        except Exception as exc:
            raise DriveOauthExchangeError("Could not exchange Drive OAuth code.") from exc

        credentials = flow.credentials
        return DriveTokens(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expiry=credentials.expiry,
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=TOKEN_URI,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=[DRIVE_FILE_SCOPE],
        )
        try:
            credentials.refresh(Request())
        except Exception as exc:
            raise DriveTokenInvalidError("Could not refresh Drive access token.") from exc
        return credentials.token

    def find_or_create_folder(
        self,
        access_token: str,
        folder_name: str,
        parent_folder_id: str | None = None,
    ) -> DriveFolder:
        service = self._drive_service(access_token)
        query_parts = [
            "mimeType='application/vnd.google-apps.folder'",
            f"name='{_escape_drive_query(folder_name)}'",
            "trashed=false",
        ]
        if parent_folder_id:
            query_parts.append(f"'{_escape_drive_query(parent_folder_id)}' in parents")
        search = service.files().list(
            q=" and ".join(query_parts),
            spaces="drive",
            fields="files(id,name)",
        ).execute()
        files = search.get("files", [])
        if files:
            existing = files[0]
            return DriveFolder(
                folder_id=existing["id"],
                name=existing.get("name", folder_name),
            )

        try:
            body = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_folder_id:
                body["parents"] = [parent_folder_id]
            created = service.files().create(
                body=body,
                fields="id,name",
            ).execute()
        except Exception as exc:
            raise DriveFolderCreateError(
                "Could not create the SADify Projects folder."
            ) from exc
        return DriveFolder(
            folder_id=created["id"],
            name=created.get("name", folder_name),
        )

    def list_subfolders(
        self,
        *,
        access_token: str,
        parent_folder_id: str,
    ) -> list[DriveFolderRef]:
        service = self._drive_service(access_token)
        try:
            result = service.files().list(
                q=" and ".join(
                    [
                        "mimeType='application/vnd.google-apps.folder'",
                        f"'{_escape_drive_query(parent_folder_id)}' in parents",
                        "trashed=false",
                    ]
                ),
                spaces="drive",
                fields="files(id,name,mimeType,createdTime,webViewLink,trashed)",
            ).execute()
        except Exception as exc:
            raise DriveFolderCreateError(
                "Could not list SADify project folders."
            ) from exc

        folders = [
            DriveFolderRef(
                folder_id=item["id"],
                name=item.get("name", "Untitled Project"),
                created_time=_parse_drive_time(item.get("createdTime")),
                web_view_link=item.get("webViewLink"),
            )
            for item in result.get("files", [])
            if item.get("mimeType") == "application/vnd.google-apps.folder"
            and not item.get("trashed", False)
        ]
        return sorted(folders, key=lambda folder: folder.created_time)

    def upload_markdown_as_doc(
        self,
        *,
        access_token: str,
        folder_id: str,
        title: str,
        markdown: str,
    ) -> DriveUploadResult:
        service = self._drive_service(access_token)
        media = MediaIoBaseUpload(
            BytesIO(markdown.encode("utf-8")),
            mimetype="text/markdown",
            resumable=False,
        )
        try:
            created = service.files().create(
                body={
                    "name": title,
                    "parents": [folder_id],
                    "mimeType": "application/vnd.google-apps.document",
                },
                media_body=media,
                fields="id,webViewLink",
            ).execute()
        except Exception as exc:
            raise DriveUploadError("Google Drive rejected the upload.") from exc
        return DriveUploadResult(
            file_id=created["id"],
            web_view_link=created["webViewLink"],
        )

    def find_file_in_folder(
        self,
        *,
        access_token: str,
        folder_id: str,
        name: str,
        mime_type: str | None = None,
    ) -> DriveFileRef | None:
        service = self._drive_service(access_token)
        query_parts = [
            f"'{_escape_drive_query(folder_id)}' in parents",
            f"name='{_escape_drive_query(name)}'",
            "trashed=false",
        ]
        if mime_type:
            query_parts.append(f"mimeType='{_escape_drive_query(mime_type)}'")
        try:
            result = service.files().list(
                q=" and ".join(query_parts),
                spaces="drive",
                fields="files(id,name,mimeType,webViewLink,md5Checksum)",
            ).execute()
        except Exception as exc:
            raise DriveTextFileError("Could not find Drive text file.") from exc

        files = result.get("files", [])
        if not files:
            return None
        item = files[0]
        return DriveFileRef(
            file_id=item["id"],
            name=item.get("name", name),
            mime_type=item.get("mimeType"),
            web_view_link=item.get("webViewLink"),
            md5_checksum=item.get("md5Checksum"),
        )

    def download_text_file(self, *, access_token: str, file_id: str) -> str:
        service = self._drive_service(access_token)
        try:
            raw = service.files().get_media(fileId=file_id).execute()
        except Exception as exc:
            raise DriveTextFileError("Could not download Drive text file.") from exc
        if isinstance(raw, str):
            return raw
        return raw.decode("utf-8")

    def upload_or_replace_text_file(
        self,
        *,
        access_token: str,
        folder_id: str,
        name: str,
        mime_type: str,
        content: str,
        existing_file_id: str | None = None,
    ) -> DriveUploadResult:
        service = self._drive_service(access_token)
        media = MediaInMemoryUpload(
            content.encode("utf-8"),
            mimetype=mime_type,
            resumable=False,
        )
        body = {"name": name, "mimeType": mime_type}
        try:
            if existing_file_id:
                result = service.files().update(
                    fileId=existing_file_id,
                    body=body,
                    media_body=media,
                    fields="id,webViewLink",
                ).execute()
            else:
                result = service.files().create(
                    body={
                        **body,
                        "parents": [folder_id],
                    },
                    media_body=media,
                    fields="id,webViewLink",
                ).execute()
        except Exception as exc:
            raise DriveTextFileError("Could not upload Drive text file.") from exc
        return DriveUploadResult(
            file_id=result["id"],
            web_view_link=result["webViewLink"],
        )

    def _drive_service(self, access_token: str):
        credentials = Credentials(token=access_token)
        return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _client_config(client_id: str, client_secret: str) -> dict[str, dict[str, object]]:
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
        }
    }


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _parse_drive_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
