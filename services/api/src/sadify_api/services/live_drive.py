from sadify_api.config import ApiConfig
from sadify_api.services.drive_client import DriveClient
from sadify_api.services.secret_store import SecretStore, get_secret_store


class LiveDriveServicesDisabledError(Exception):
    pass


def resolve_live_drive_services(
    config: ApiConfig,
    drive_client: DriveClient | None,
    secret_store: SecretStore | None,
) -> tuple[DriveClient, SecretStore]:
    if drive_client is not None and secret_store is not None:
        return drive_client, secret_store
    if not config.drive_live_enabled:
        raise LiveDriveServicesDisabledError()

    resolved_secret_store = secret_store or get_secret_store(
        project_id=config.google_cloud_project,
        oauth_client_secret_name=config.google_oauth_client_secret_name,
    )
    resolved_drive_client = drive_client or DriveClient(
        client_id=config.google_oauth_client_id,
        client_secret=resolved_secret_store.get_oauth_client_secret(),
    )
    return resolved_drive_client, resolved_secret_store
