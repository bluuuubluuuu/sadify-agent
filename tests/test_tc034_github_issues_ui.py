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
    # Per-user: the repo is supplied by the user, no longer a setup blocker.
    assert "GITHUB_REPO_NOT_CONFIGURED" not in hook
    # Pasted PAT held in memory and sent on approve; repo sent on prepare.
    assert "setGithubToken" in hook
    assert "githubToken: githubToken || undefined" in hook
    assert "repo?: string | null" in hook
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
    assert "View SAD preview" in timeline
    assert "onViewSavedSad" in timeline
    assert "View developer handoff" not in timeline
    assert "Open the developer handoff panel to prepare GitHub issues" not in timeline
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


def test_connect_github_modal_collects_token_repo_with_instructions():
    modal = (WEB_SRC / "components" / "agent" / "ConnectGithubModal.tsx").read_text(
        encoding="utf-8"
    )

    assert "Connect GitHub" in modal
    # Token + repo inputs.
    assert 'type="password"' in modal
    assert "owner/name" in modal
    # Inline create-PAT instructions + Issues permission guidance.
    assert "fine-grained personal access token" in modal
    assert "Issues: Read and write" in modal
    # Honest session-only security copy.
    assert "Stored only for this session, never saved" in modal
    assert "onSubmit(token.trim(), repo.trim())" in modal


def test_sidebar_shows_per_project_github_link():
    project_list = (WEB_SRC / "components" / "shell" / "ProjectList.tsx").read_text(
        encoding="utf-8"
    )

    assert "project.github_repo" in project_list
    assert "projectGithubUrl" in project_list
    assert "https://github.com/${repo}" in project_list
    assert "<span>GitHub</span>" in project_list


def test_workspace_hydrates_agent_saved_sad_into_preview_pane():
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(
        encoding="utf-8"
    )
    readiness = (WEB_SRC / "components" / "chat" / "ReadinessPane.tsx").read_text(
        encoding="utf-8"
    )
    sad_save_hook = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(
        encoding="utf-8"
    )

    assert "useAgentGithubIssues" in workspace
    assert "const githubIssues = useAgentGithubIssues" in workspace
    assert "AgentHandoffPane" not in workspace
    assert "agent.savedPreviewId" not in workspace
    assert "adoptAgentSave" in sad_save_hook
    assert "onSaved: (savedSad)" in workspace
    assert "sadSave.adoptAgentSave(savedSad)" in workspace
    assert "PreviewPane" in workspace
    # Per-user GitHub connect gates prepare via a modal + persists the repo.
    assert "onPrepareGithubIssues={handlePrepareGithubIssues}" in workspace
    assert "ConnectGithubModal" in workspace
    assert "setProjectGithubRepo" in workspace
    assert 'mode="github"' in workspace
    assert "onApprove={() => githubIssues.approve()}" in workspace
    assert "githubIssues.setupNotice" in workspace
    assert "export function AgentHandoffPane" not in readiness
    assert "SAD saved by agent" not in readiness
    assert "Developer handoff is ready" not in readiness
    # GitHub approval stays out of the Drive/wiki finalizer hook.
    finalize_hook = (WEB_SRC / "lib" / "hooks" / "useAgentFinalize.ts").read_text(
        encoding="utf-8"
    )
    assert "/agent/github/issues/approve" not in finalize_hook
    assert "approveAgentGithubIssues" not in finalize_hook
    assert "savedSad" in finalize_hook
    assert "completed_actions" in finalize_hook
