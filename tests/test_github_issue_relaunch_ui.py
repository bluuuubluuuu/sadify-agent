from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def _read(relative_path: str) -> str:
    return (WEB_SRC / relative_path).read_text(encoding="utf-8")


def _prepare_function(api: str) -> str:
    start = api.index("export async function prepareAgentGithubIssues")
    end = api.index("export async function approveAgentGithubIssues", start)
    return api[start:end]


def test_prepare_is_saved_sad_scoped_and_authenticated():
    api = _read("lib/api.ts")
    hook = _read("lib/hooks/useAgentGithubIssues.ts")
    prepare = _prepare_function(api)

    assert "saveId: string" in api
    assert "previewId: string" not in prepare
    assert 'Authorization: `Bearer ${idToken}`' in prepare
    assert "getFirebaseAuth().currentUser" in hook


def test_api_and_hook_expose_relaunch():
    api = _read("lib/api.ts")
    hook = _read("lib/hooks/useAgentGithubIssues.ts")

    assert "relaunchAgentGithubIssues" in api
    assert "/agent/github/issues/relaunch" in api
    assert "async function relaunch" in hook


def test_result_contract_has_created_skipped_totals():
    api = _read("lib/api.ts")
    hook = _read("lib/hooks/useAgentGithubIssues.ts")

    for token in ("created_issues", "skipped_issues", "totals"):
        assert token in api
        assert token in hook


def test_history_action_is_resume_only():
    api = _read("lib/api.ts")
    history = _read("components/shell/SaveHistory.tsx")

    assert "has_github_issue_set: boolean" in api
    assert "save.has_github_issue_set" in history
    assert "Create GitHub issues" in history
    assert "onCreateGithubIssues" in history


def test_resume_wires_history_to_relaunch_and_locked_modal():
    sidebar = _read("components/shell/Sidebar.tsx")
    workspace = _read("components/WorkspaceV2.tsx")
    modal = _read("components/agent/ConnectGithubModal.tsx")

    assert "onCreateGithubIssues" in sidebar
    assert "githubIssues.relaunch" in workspace
    assert "lockedRepo" in workspace
    assert "repoLocked" in modal
    assert "disabled={repoLocked}" in modal


def test_timeline_displays_created_and_skipped_totals():
    timeline = _read("components/agent/AgentTimeline.tsx")

    assert "totals.created" in timeline
    assert "totals.skipped" in timeline
