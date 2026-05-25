from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


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
class DriveUploadResult:
    file_id: str
    web_view_link: str


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

    def find_or_create_folder(self, access_token: str, folder_name: str) -> DriveFolder:
        service = self._drive_service(access_token)
        query = (
            "mimeType='application/vnd.google-apps.folder' "
            f"and name='{folder_name}' and trashed=false"
        )
        search = service.files().list(
            q=query,
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
            created = service.files().create(
                body={
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                },
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
