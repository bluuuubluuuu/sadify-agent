import asyncio

from services.mcp.github_server import (
    GitHubIssue,
    GitHubIssueBatch,
    create_github_issues_payload,
)


def test_create_github_issues_posts_well_formed_payloads():
    client = FakeGitHubClient(
        [
            FakeGitHubResponse(
                201,
                {
                    "number": 101,
                    "html_url": "https://github.com/acme/app/issues/101",
                },
            ),
            FakeGitHubResponse(
                201,
                {
                    "number": 102,
                    "html_url": "https://github.com/acme/app/issues/102",
                },
            ),
        ]
    )

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="acme/app",
                issues=[
                    GitHubIssue(
                        title="Build appointment workflow",
                        body="Implement the appointment workflow from SRC-000001.",
                        labels=["sadify", "high-priority"],
                    ),
                    GitHubIssue(
                        title="Add manager reports",
                        body="Create the manager reporting view from SRC-000002.",
                    ),
                ],
            ),
            configured_repo="acme/app",
            token_provider=lambda: "ghp_secret",
            client_factory=lambda: client,
        )
    )

    assert result == {
        "status": "created",
        "repo": "acme/app",
        "issues": [
            {
                "number": 101,
                "url": "https://github.com/acme/app/issues/101",
                "title": "Build appointment workflow",
            },
            {
                "number": 102,
                "url": "https://github.com/acme/app/issues/102",
                "title": "Add manager reports",
            },
        ],
    }
    assert [call["url"] for call in client.calls] == [
        "https://api.github.com/repos/acme/app/issues",
        "https://api.github.com/repos/acme/app/issues",
    ]
    assert client.calls[0]["headers"]["Authorization"] == "Bearer ghp_secret"
    assert client.calls[0]["json"] == {
        "title": "Build appointment workflow",
        "body": "Implement the appointment workflow from SRC-000001.",
        "labels": ["sadify", "high-priority"],
    }
    assert client.calls[1]["json"] == {
        "title": "Add manager reports",
        "body": "Create the manager reporting view from SRC-000002.",
    }


def test_create_github_issues_refuses_missing_token_without_calling_api():
    client = FakeGitHubClient([])

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="acme/app",
                issues=[
                    GitHubIssue(
                        title="Build appointment workflow",
                        body="Implement the appointment workflow.",
                    )
                ],
            ),
            configured_repo="acme/app",
            token_provider=lambda: "",
            client_factory=lambda: client,
        )
    )

    assert result == {
        "status": "error",
        "code": "GITHUB_TOKEN_MISSING",
        "message": "Set SADIFY_GITHUB_TOKEN before creating GitHub issues.",
    }
    assert client.calls == []


def test_create_github_issues_rejects_unconfigured_repo_without_calling_api():
    client = FakeGitHubClient([])

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="other/app",
                issues=[
                    GitHubIssue(
                        title="Build appointment workflow",
                        body="Implement the appointment workflow.",
                    )
                ],
            ),
            configured_repo="acme/app",
            token_provider=lambda: "ghp_secret",
            client_factory=lambda: client,
        )
    )

    assert result == {
        "status": "error",
        "code": "GITHUB_REPO_NOT_ALLOWED",
        "message": "This MCP server is configured only for repo acme/app.",
    }
    assert client.calls == []


def test_create_github_issues_surfaces_api_error_without_leaking_token():
    client = FakeGitHubClient(
        [
            FakeGitHubResponse(
                422,
                {"message": "Validation Failed"},
            )
        ]
    )

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="acme/app",
                issues=[
                    GitHubIssue(
                        title="Build appointment workflow",
                        body="Implement the appointment workflow.",
                    )
                ],
            ),
            configured_repo="acme/app",
            token_provider=lambda: "ghp_secret",
            client_factory=lambda: client,
        )
    )

    assert result == {
        "status": "error",
        "code": "GITHUB_API_ERROR",
        "message": "GitHub issue creation failed with status 422: Validation Failed.",
    }
    assert "ghp_secret" not in str(result)


class FakeGitHubClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, *, headers, json):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self.responses.pop(0)


class FakeGitHubResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload
