from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_github_issue_api_contract_is_separate_from_drive_approve():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type AgentGithubIssue" in api
    assert "export async function prepareAgentGithubIssues" in api
    assert "export async function approveAgentGithubIssues" in api
    assert "/agent/github/issues/prepare" in api
    assert "/agent/github/issues/approve" in api
    assert "/agent/approve" in api
    assert "Authorization: `Bearer ${idToken}`" in api
    assert "SADify agent could not prepare GitHub issues yet." in api
    assert "SADify agent could not create GitHub issues yet." in api


def test_github_issue_hook_prepares_then_approves_with_firebase_auth():
    hook = (WEB_SRC / "lib" / "hooks" / "useAgentGithubIssues.ts").read_text(
        encoding="utf-8"
    )

    assert "prepareAgentGithubIssues" in hook
    assert "approveAgentGithubIssues" in hook
    assert "getFirebaseAuth().currentUser" in hook
    assert "user.getIdToken()" in hook
    assert "status === 401 || error.status === 403" in hook
    assert "Sign in with Google before creating GitHub issues." in hook
    assert "GITHUB_MCP_DISABLED" in hook
    assert "GITHUB_REPO_NOT_CONFIGURED" in hook
    assert "setSetupNotice" in hook
    assert "setIsPreparing(true)" in hook


def test_agent_timeline_renders_distinct_github_approval_and_results():
    timeline = (WEB_SRC / "components" / "agent" / "AgentTimeline.tsx").read_text(
        encoding="utf-8"
    )
    css = (WEB_SRC / "components" / "agent" / "agent.module.css").read_text(
        encoding="utf-8"
    )

    assert 'mode === "github"' in timeline
    assert "Create {issueCount} GitHub issues in {repo}" in timeline
    assert "Approve &amp; create issues" in timeline
    assert "GitHub issues created" in timeline
    assert "Open issue" in timeline
    assert "githubIssueList" in timeline
    assert ".githubIssueList" in css
    assert ".githubRepo" in css
    # The GitHub branch must not borrow the Drive/wiki save wording.
    assert "Approve &amp; save" in timeline
    assert "Approve &amp; create issues" in timeline


def test_preview_pane_exposes_post_save_github_cta_and_setup_notice():
    preview = (WEB_SRC / "components" / "preview" / "PreviewPane.tsx").read_text(
        encoding="utf-8"
    )
    css = (WEB_SRC / "components" / "preview" / "PreviewPane.module.css").read_text(
        encoding="utf-8"
    )

    assert "onPrepareGithubIssues?: () => void" in preview
    assert "Prepare GitHub issues" in preview
    assert "githubSetupNotice" in preview
    assert "isGithubPreparing" in preview
    assert "Boolean(record) && onPrepareGithubIssues" in preview
    assert ".githubHandoff" in css
    assert ".setupNotice" in css


def test_workspace_wires_separate_github_issue_flow():
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(
        encoding="utf-8"
    )

    assert "useAgentGithubIssues" in workspace
    assert "const githubIssues = useAgentGithubIssues" in workspace
    assert "onPrepareGithubIssues={() => githubIssues.prepare(sadSave.previewId)}" in workspace
    assert 'mode="github"' in workspace
    assert "onApprove={() => githubIssues.approve()}" in workspace
    assert "githubIssues.setupNotice" in workspace
    # GitHub approval stays out of the Drive/wiki finalizer hook.
    finalize_hook = (WEB_SRC / "lib" / "hooks" / "useAgentFinalize.ts").read_text(
        encoding="utf-8"
    )
    assert "/agent/github/issues/approve" not in finalize_hook
    assert "approveAgentGithubIssues" not in finalize_hook
