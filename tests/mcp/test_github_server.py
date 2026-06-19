import asyncio

from services.mcp.github_server import (
    GitHubIssue,
    GitHubIssueBatch,
    create_github_issues_payload,
)


def test_create_github_issues_posts_well_formed_payloads():
    client = FakeGitHubClient(
        get_responses=[FakeGitHubResponse(200, [])],
        post_responses=[
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
                        marker="<!-- sadify-github-issue:PR-1:SV-1:0 -->",
                        title="Build appointment workflow",
                        body=(
                            "Implement the appointment workflow from SRC-000001.\n\n"
                            "<!-- sadify-github-issue:PR-1:SV-1:0 -->"
                        ),
                        labels=["sadify", "high-priority"],
                    ),
                    GitHubIssue(
                        marker="<!-- sadify-github-issue:PR-1:SV-1:1 -->",
                        title="Add manager reports",
                        body=(
                            "Create the manager reporting view from SRC-000002.\n\n"
                            "<!-- sadify-github-issue:PR-1:SV-1:1 -->"
                        ),
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
        "created_issues": [
            {
                "number": 101,
                "url": "https://github.com/acme/app/issues/101",
                "title": "Build appointment workflow",
                "marker": "<!-- sadify-github-issue:PR-1:SV-1:0 -->",
            },
            {
                "number": 102,
                "url": "https://github.com/acme/app/issues/102",
                "title": "Add manager reports",
                "marker": "<!-- sadify-github-issue:PR-1:SV-1:1 -->",
            },
        ],
        "skipped_issues": [],
        "totals": {"requested": 2, "created": 2, "skipped": 0},
    }
    assert [call["url"] for call in client.post_calls] == [
        "https://api.github.com/repos/acme/app/issues",
        "https://api.github.com/repos/acme/app/issues",
    ]
    assert client.post_calls[0]["headers"]["Authorization"] == "Bearer ghp_secret"
    assert client.post_calls[0]["json"] == {
        "title": "Build appointment workflow",
        "body": (
            "Implement the appointment workflow from SRC-000001.\n\n"
            "<!-- sadify-github-issue:PR-1:SV-1:0 -->"
        ),
        "labels": ["sadify", "high-priority"],
    }
    assert client.post_calls[1]["json"] == {
        "title": "Add manager reports",
        "body": (
            "Create the manager reporting view from SRC-000002.\n\n"
            "<!-- sadify-github-issue:PR-1:SV-1:1 -->"
        ),
    }


def test_create_github_issues_refuses_missing_token_without_calling_api():
    client = FakeGitHubClient()

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="acme/app",
                issues=[
                    GitHubIssue(
                        marker="<!-- sadify-github-issue:PR-1:SV-1:0 -->",
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
    assert client.get_calls == []
    assert client.post_calls == []


def test_create_github_issues_approval_mode_returns_proposal_without_token_or_api_call():
    client = FakeGitHubClient()

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="acme/app",
                issues=[
                    GitHubIssue(
                        marker="<!-- sadify-github-issue:PR-1:SV-1:0 -->",
                        title="Build appointment workflow",
                        body="Implement the appointment workflow.",
                        labels=["sadify", "priority-high"],
                    )
                ],
            ),
            configured_repo="acme/app",
            token_provider=lambda: "",
            client_factory=lambda: client,
            approval_required=True,
        )
    )

    assert result == {
        "approval_required": True,
        "tool": "create_github_issues",
        "repo": "acme/app",
        "proposed_actions": [
            {
                "id": "create_github_issues",
                "label": "Create GitHub issues",
                "repo": "acme/app",
                "issue_count": 1,
                "issues": [
                    {
                        "marker": "<!-- sadify-github-issue:PR-1:SV-1:0 -->",
                        "title": "Build appointment workflow",
                        "body": "Implement the appointment workflow.",
                        "labels": ["sadify", "priority-high"],
                    }
                ],
            }
        ],
    }
    assert client.get_calls == []
    assert client.post_calls == []


def test_create_github_issues_rejects_unconfigured_repo_without_calling_api():
    client = FakeGitHubClient()

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="other/app",
                issues=[
                    GitHubIssue(
                        marker="<!-- sadify-github-issue:PR-1:SV-1:0 -->",
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
    assert client.get_calls == []
    assert client.post_calls == []


def test_create_github_issues_surfaces_api_error_without_leaking_token():
    client = FakeGitHubClient(
        get_responses=[FakeGitHubResponse(200, [])],
        post_responses=[
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
                        marker="<!-- sadify-github-issue:PR-1:SV-1:0 -->",
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
        "repo": "acme/app",
        "created_issues": [],
        "skipped_issues": [],
        "totals": {"requested": 1, "created": 0, "skipped": 0},
    }
    assert "ghp_secret" not in str(result)


def test_create_github_issues_skips_marker_across_pages_and_excludes_pull_requests():
    marker = "<!-- sadify-github-issue:PR-1:SV-1:0 -->"
    first_page = [
        {
            "number": index,
            "html_url": f"https://github.com/acme/app/issues/{index}",
            "title": f"Issue {index}",
            "body": "No SADify marker",
        }
        for index in range(1, 101)
    ]
    client = FakeGitHubClient(
        get_responses=[
            FakeGitHubResponse(200, first_page),
            FakeGitHubResponse(
                200,
                [
                    {
                        "number": 101,
                        "html_url": "https://github.com/acme/app/issues/101",
                        "title": "Renamed task",
                        "body": marker,
                    },
                    {
                        "number": 102,
                        "html_url": "https://github.com/acme/app/pull/102",
                        "title": "Pull request",
                        "body": marker,
                        "pull_request": {},
                    },
                ],
            ),
        ]
    )

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="acme/app",
                issues=[GitHubIssue(marker=marker, title="Original task", body=marker)],
            ),
            configured_repo="acme/app",
            token_provider=lambda: "ghp_secret",
            client_factory=lambda: client,
        )
    )

    assert result["status"] == "created"
    assert result["created_issues"] == []
    assert result["skipped_issues"] == [
        {
            "number": 101,
            "url": "https://github.com/acme/app/issues/101",
            "title": "Renamed task",
            "marker": marker,
        }
    ]
    assert result["totals"] == {"requested": 1, "created": 0, "skipped": 1}
    assert [call["params"]["page"] for call in client.get_calls] == [1, 2]
    assert client.post_calls == []


def test_matching_title_without_marker_is_created():
    marker = "<!-- sadify-github-issue:PR-1:SV-1:0 -->"
    client = FakeGitHubClient(
        get_responses=[
            FakeGitHubResponse(
                200,
                [{"number": 4, "title": "Same title", "body": "Different body"}],
            )
        ],
        post_responses=[
            FakeGitHubResponse(
                201,
                {"number": 5, "html_url": "https://github.com/acme/app/issues/5"},
            )
        ],
    )

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(
                repo="acme/app",
                issues=[GitHubIssue(marker=marker, title="Same title", body=marker)],
            ),
            configured_repo="acme/app",
            token_provider=lambda: "ghp_secret",
            client_factory=lambda: client,
        )
    )

    assert result["totals"] == {"requested": 1, "created": 1, "skipped": 0}


def test_partial_failure_reports_created_progress():
    client = FakeGitHubClient(
        get_responses=[FakeGitHubResponse(200, [])],
        post_responses=[
            FakeGitHubResponse(
                201,
                {"number": 1, "html_url": "https://github.com/acme/app/issues/1"},
            ),
            FakeGitHubResponse(502, {"message": "Upstream failed"}),
        ],
    )
    issues = [
        GitHubIssue(
            marker=f"<!-- sadify-github-issue:PR-1:SV-1:{index} -->",
            title=f"Task {index}",
            body=f"Body {index}",
        )
        for index in range(2)
    ]

    result = asyncio.run(
        create_github_issues_payload(
            GitHubIssueBatch(repo="acme/app", issues=issues),
            configured_repo="acme/app",
            token_provider=lambda: "ghp_secret",
            client_factory=lambda: client,
        )
    )

    assert result["status"] == "error"
    assert result["totals"] == {"requested": 2, "created": 1, "skipped": 0}
    assert [issue["number"] for issue in result["created_issues"]] == [1]


class FakeGitHubClient:
    def __init__(self, *, get_responses=None, post_responses=None):
        self.get_responses = list(get_responses or [])
        self.post_responses = list(post_responses or [])
        self.get_calls = []
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def get(self, url, *, headers, params):
        self.get_calls.append({"url": url, "headers": headers, "params": params})
        return self.get_responses.pop(0)

    async def post(self, url, *, headers, json):
        self.post_calls.append({"url": url, "headers": headers, "json": json})
        return self.post_responses.pop(0)


class FakeGitHubResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload
