"""Standalone stdio MCP server for creating GitHub issues from SADify tasks."""

from collections.abc import Callable
import os
from typing import Any, Protocol

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator


GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_TOKEN_ENV = "SADIFY_GITHUB_TOKEN"
GITHUB_REPO_ENV = "SADIFY_GITHUB_REPO"

mcp = FastMCP(
    "github_mcp",
    instructions=(
        "Create GitHub issues only in the configured SADify repository. "
        "This server never deletes, edits, closes, or reads secrets aloud."
    ),
)


class GitHubIssue(BaseModel):
    """A single GitHub issue to create."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(
        min_length=1,
        max_length=256,
        description="GitHub issue title.",
    )
    body: str = Field(
        min_length=1,
        max_length=65536,
        description="GitHub issue body, including SAD/source traceability.",
    )
    labels: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Optional GitHub labels to apply.",
    )

    @field_validator("labels")
    @classmethod
    def _labels_must_be_non_empty(cls, labels: list[str]) -> list[str]:
        cleaned = [label.strip() for label in labels if label.strip()]
        if len(cleaned) != len(labels):
            raise ValueError("labels must not contain blank values")
        return cleaned


class GitHubIssueBatch(BaseModel):
    """Input batch for GitHub issue creation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    repo: str = Field(
        min_length=3,
        max_length=200,
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        description="Target GitHub repository in owner/name form.",
    )
    issues: list[GitHubIssue] = Field(
        min_length=1,
        max_length=20,
        description="Developer tasks to create as GitHub issues.",
    )


class AsyncGitHubClient(Protocol):
    async def __aenter__(self) -> "AsyncGitHubClient": ...

    async def __aexit__(self, exc_type, exc, traceback) -> object: ...

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> Any: ...


TokenProvider = Callable[[], str | None]
ClientFactory = Callable[[], AsyncGitHubClient]


@mcp.tool(
    name="create_github_issues",
    title="Create GitHub Issues",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def create_github_issues(repo: str, issues: list[GitHubIssue]) -> dict[str, Any]:
    """Create GitHub issues in the configured repository.

    Args:
        repo: Target repository in owner/name form. Must match SADIFY_GITHUB_REPO.
        issues: Developer tasks to create. Each issue has title, body, labels.

    Returns:
        A dictionary with status="created" and created issue numbers/URLs, or
        status="error" with a safe code/message. The GitHub token is never
        returned or logged.
    """

    return await create_github_issues_payload(
        GitHubIssueBatch(repo=repo, issues=issues),
    )


async def create_github_issues_payload(
    batch: GitHubIssueBatch,
    *,
    configured_repo: str | None = None,
    token_provider: TokenProvider | None = None,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Create issues with injectable auth/client seams for tests and future Secret Manager."""

    allowed_repo = configured_repo if configured_repo is not None else _configured_repo()
    if not allowed_repo:
        return {
            "status": "error",
            "code": "GITHUB_REPO_NOT_CONFIGURED",
            "message": f"Set {GITHUB_REPO_ENV} to the allowed GitHub repo.",
        }
    if _normalize_repo(batch.repo) != _normalize_repo(allowed_repo):
        return {
            "status": "error",
            "code": "GITHUB_REPO_NOT_ALLOWED",
            "message": f"This MCP server is configured only for repo {allowed_repo}.",
        }

    token = (token_provider or _github_token)()
    if not token:
        return {
            "status": "error",
            "code": "GITHUB_TOKEN_MISSING",
            "message": f"Set {GITHUB_TOKEN_ENV} before creating GitHub issues.",
        }

    headers = _github_headers(token)
    created: list[dict[str, Any]] = []
    factory = client_factory or _github_client_factory
    async with factory() as client:
        for issue in batch.issues:
            response = await client.post(
                f"{GITHUB_API_BASE_URL}/repos/{allowed_repo}/issues",
                headers=headers,
                json=_issue_payload(issue),
            )
            if response.status_code != 201:
                return _github_api_error(response)
            payload = response.json()
            created.append(
                {
                    "number": payload.get("number"),
                    "url": payload.get("html_url"),
                    "title": issue.title,
                }
            )

    return {"status": "created", "repo": allowed_repo, "issues": created}


def _configured_repo() -> str | None:
    return os.getenv(GITHUB_REPO_ENV)


def _github_token() -> str | None:
    return os.getenv(GITHUB_TOKEN_ENV)


def _github_client_factory() -> AsyncGitHubClient:
    return httpx.AsyncClient(timeout=30.0)


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _issue_payload(issue: GitHubIssue) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": issue.title,
        "body": issue.body,
    }
    if issue.labels:
        payload["labels"] = list(issue.labels)
    return payload


def _github_api_error(response: Any) -> dict[str, Any]:
    message = _github_error_message(response)
    return {
        "status": "error",
        "code": "GITHUB_API_ERROR",
        "message": (
            f"GitHub issue creation failed with status {response.status_code}: "
            f"{message}."
        ),
    }


def _github_error_message(response: Any) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "Unexpected response from GitHub"
    message = payload.get("message") if isinstance(payload, dict) else None
    return str(message or "Unexpected response from GitHub")


def _normalize_repo(repo: str) -> str:
    return repo.strip().lower()


if __name__ == "__main__":
    mcp.run()
