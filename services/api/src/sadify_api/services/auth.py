from dataclasses import dataclass
from typing import Protocol

from sadify_api.config import ApiConfig


@dataclass(frozen=True)
class VerifiedFirebaseUser:
    uid: str
    email: str | None = None
    display_name: str | None = None
    provider: str = "firebase"


class AuthVerificationError(Exception):
    pass


class TokenVerifier(Protocol):
    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        pass


class FirebaseAdminTokenVerifier:
    def __init__(self, config: ApiConfig) -> None:
        self._config = config

    def verify_id_token(self, id_token: str) -> VerifiedFirebaseUser:
        try:
            decoded_token = self._verify_with_firebase_admin(id_token)
        except Exception as exc:
            raise AuthVerificationError("invalid Firebase ID token") from exc

        return VerifiedFirebaseUser(
            uid=str(decoded_token["uid"]),
            email=decoded_token.get("email"),
            display_name=decoded_token.get("name"),
        )

    def _verify_with_firebase_admin(self, id_token: str) -> dict:
        import firebase_admin
        from firebase_admin import auth

        if not firebase_admin._apps:
            options = {}
            if self._config.firebase_project_id:
                options["projectId"] = self._config.firebase_project_id
            firebase_admin.initialize_app(options=options)

        return auth.verify_id_token(id_token)
