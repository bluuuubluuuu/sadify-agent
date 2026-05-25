from __future__ import annotations

import re

from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

from sadify_api.config import load_api_config


_SAFE_UID = re.compile(r"^[A-Za-z0-9_-]+$")


class SecretStore:
    def __init__(
        self,
        *,
        project_id: str,
        oauth_client_secret_name: str = "sadify-drive-oauth-client-secret",
        client: secretmanager.SecretManagerServiceClient | None = None,
    ) -> None:
        if not project_id:
            raise ValueError("Google Cloud project is required for Secret Manager.")
        self.project_id = project_id
        self.oauth_client_secret_name = oauth_client_secret_name
        self.client = client or secretmanager.SecretManagerServiceClient()

    def get_oauth_client_secret(self) -> str:
        response = self.client.access_secret_version(
            request={"name": self._latest_version_name(self.oauth_client_secret_name)}
        )
        return response.payload.data.decode("utf-8")

    def put_user_refresh_token(self, uid: str, refresh_token: str) -> None:
        secret_name = self._user_secret_name(uid)
        secret_path = self._secret_path(secret_name)
        try:
            self.client.get_secret(request={"name": secret_path})
        except NotFound:
            self.client.create_secret(
                request={
                    "parent": f"projects/{self.project_id}",
                    "secret_id": secret_name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        self.client.add_secret_version(
            request={
                "parent": secret_path,
                "payload": {"data": refresh_token.encode("utf-8")},
            }
        )

    def get_user_refresh_token(self, uid: str) -> str | None:
        try:
            response = self.client.access_secret_version(
                request={"name": self._latest_version_name(self._user_secret_name(uid))}
            )
        except NotFound:
            return None
        return response.payload.data.decode("utf-8")

    def delete_user_secret(self, uid: str) -> None:
        try:
            self.client.delete_secret(
                request={"name": self._secret_path(self._user_secret_name(uid))}
            )
        except NotFound:
            return

    def _latest_version_name(self, secret_name: str) -> str:
        return self.client.secret_version_path(self.project_id, secret_name, "latest")

    def _secret_path(self, secret_name: str) -> str:
        return self.client.secret_path(self.project_id, secret_name)

    def _user_secret_name(self, uid: str) -> str:
        if not _SAFE_UID.match(uid):
            raise ValueError("Firebase uid contains unsupported characters.")
        return f"sadify-drive-token-{uid}"


_secret_store: SecretStore | None = None


def get_secret_store(
    *,
    project_id: str | None = None,
    oauth_client_secret_name: str | None = None,
    force_new: bool = False,
) -> SecretStore:
    global _secret_store
    if _secret_store is not None and not force_new:
        return _secret_store

    config = load_api_config()
    resolved_project = project_id or config.google_cloud_project
    resolved_secret_name = (
        oauth_client_secret_name
        or getattr(config, "google_oauth_client_secret_name", None)
        or "sadify-drive-oauth-client-secret"
    )
    _secret_store = SecretStore(
        project_id=resolved_project or "",
        oauth_client_secret_name=resolved_secret_name,
    )
    return _secret_store
