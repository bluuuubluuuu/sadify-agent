from fastapi import APIRouter, Header, HTTPException

from sadify_api.schemas import AuthenticatedUser, AuthSessionResponse
from sadify_api.services.auth import AuthVerificationError, TokenVerifier


def create_auth_router(token_verifier: TokenVerifier) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/session", response_model=AuthSessionResponse)
    def create_session(
        authorization: str | None = Header(default=None),
    ) -> AuthSessionResponse:
        user = verify_authorization_header(authorization, token_verifier)
        return AuthSessionResponse(status="authenticated", user=user)

    @router.get("/me", response_model=AuthSessionResponse)
    def get_me(
        authorization: str | None = Header(default=None),
    ) -> AuthSessionResponse:
        user = verify_authorization_header(authorization, token_verifier)
        return AuthSessionResponse(status="authenticated", user=user)

    return router


def verify_authorization_header(
    authorization: str | None,
    token_verifier: TokenVerifier,
) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    id_token = authorization.removeprefix("Bearer ").strip()
    if not id_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        verified = token_verifier.verify_id_token(id_token)
    except AuthVerificationError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        ) from exc

    return AuthenticatedUser(
        uid=verified.uid,
        email=verified.email,
        display_name=verified.display_name,
        provider=verified.provider,
    )


_verify_authorization_header = verify_authorization_header
