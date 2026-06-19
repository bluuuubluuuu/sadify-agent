from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"


def _read(relative_path: str) -> str:
    path = WEB / relative_path
    assert path.exists(), f"missing frontend source: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_session_support_files_exist():
    assert (WEB / "lib" / "sessionSnapshot.ts").exists()
    assert (WEB / "lib" / "hooks" / "useProjectSession.ts").exists()


def test_api_exposes_session_client_and_wrapper_type():
    source = _read("lib/api.ts")
    assert "export type ProjectSessionSnapshot" in source
    assert "analysis_response: RequirementAnalysisApiResponse | null" in source
    assert "export async function putProjectSession" in source
    assert "export async function getProjectSession" in source
    assert "new BackendApiError" in source


def test_qna_exposes_hydration_and_carry_forward_state():
    source = _read("lib/hooks/useQnA.ts")
    assert "function hydrate" in source
    assert "setAnalysisResponse(state.analysisResponse)" in source
    assert "setAnswerHistory(state.answerHistory)" in source
    assert "answerHistory," in source
    assert "cleanRequirementText," in source


def test_write_guard_rejects_restores_empty_analysis_and_wrong_project():
    source = _read("lib/sessionSnapshot.ts")
    assert "export function shouldWriteSnapshot" in source
    assert "!hasAnalysis" in source
    assert "restoring" in source
    assert "scheduledProjectId === activeProjectId" in source


def test_project_session_hook_cancels_and_rechecks_project_when_timer_fires():
    source = _read("lib/hooks/useProjectSession.ts")
    assert "writeDebounced" in source
    assert "const cancel" in source
    assert "clearTimeout" in source
    assert "isCurrent(projectId)" in source
    assert "getProjectSession" in source
    assert "return { projectId, snapshot }" in source


def test_workspace_uses_race_safe_restore_and_effective_source_state():
    source = _read("components/WorkspaceV2.tsx")
    assert "activeProjectRef" in source
    assert "restoringRef" in source
    assert "pendingModelRef" in source
    assert "session.cancel()" in source
    assert "result.projectId !== activeProjectRef.current" in source
    assert "shouldWriteSnapshot" in source
    assert "effectiveSourceContext" in source
    assert "effectiveSourceReferences" in source
    assert "models.isLoaded" in source
