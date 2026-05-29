from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_live_gemini_qna_ui_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "AnalysisPanel.tsx",
        WEB_SRC / "components" / "WorkspaceShell.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_live_gemini_qna_ui_wires_backend_analysis_and_simple_choices():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "AnalysisPanel" in shell
    assert "analyzeRequirement" in api
    assert "/analysis/requirement" in api
    assert "readBackendError" in api
    assert "Start analysis" in panel
    assert "choices" in panel
    assert "Amend answer" in panel
    assert "No project files are written by this step." in panel


def test_live_gemini_qna_ui_shows_neutral_pre_analysis_state():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    mock_state = (WEB_SRC / "lib" / "mockState.ts").read_text(encoding="utf-8")

    assert "No analysis yet" in shell
    assert "analysis-empty-state" in shell
    assert "CurrentQuestion" not in shell
    assert 'readinessLabel: "No analysis yet"' in mock_state
    assert "categories: []" in mock_state


def test_live_gemini_qna_ui_allows_answer_choice_and_amendment_continuation():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    current_question = (WEB_SRC / "components" / "CurrentQuestion.tsx").read_text(
        encoding="utf-8"
    )

    assert "selectedChoiceId" in panel
    assert "amendmentText" in panel
    assert "continueWithAnswer" in panel
    assert "Continue with answer" in panel
    assert "Previous answer:" in panel
    assert "onAnswerSubmitted" in panel
    assert "Answer saved. Next question refreshed from Gemini." in shell
    assert "onChoiceSelect" in current_question
    assert "selectedChoiceId" in current_question


def test_live_gemini_qna_ui_preserves_answer_when_next_question_fails():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )

    assert "onAnswerKeptForPreview" in panel
    assert "Answer kept for SAD preview" in panel
    assert "Gemini could not prepare the next question" in panel
    assert "appendKeptAnswer" in panel
    assert "keptAnswerResponse" in panel
    assert "Answer kept for preview. Next question needs retry." in shell


def test_live_gemini_qna_ui_preserves_clean_requirement_for_preview():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )

    assert "cleanRequirementText" in panel
    assert "onAnalysisSaved(response, cleanRequirementText)" in panel
    assert "setAnalysisRequirementText(cleanRequirementText)" in shell


def test_live_gemini_qna_ui_makes_answer_continue_action_obvious():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    css = (WEB_SRC / "app" / "globals.css").read_text(encoding="utf-8")

    assert "answer-action-row" in panel
    assert "selectedAnswerLabel" in panel
    assert "Selected answer:" in panel
    assert "Sending answer..." in panel
    assert "Save answer and ask next question" in panel
    assert ".answer-action-row" in css
    assert ".answer-button.ready" in css


def test_live_gemini_qna_ui_labels_backend_fallback_honestly():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "isFallbackAnalysis" in panel
    assert "Fallback question shown because Gemini output was invalid." in panel
    assert "Answer saved. Fallback question shown because Gemini output was invalid." in panel


def test_live_gemini_qna_ui_supports_selection_modes_and_disabled_choices():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "selectedChoiceIds" in panel
    assert "selection_mode" in api
    assert "toggleChoice" in panel
    assert "choice.is_disabled" in panel
    assert "selectedChoiceIds.includes(choice.id)" in panel
    assert 'selection_mode === "multiple"' in panel
    assert "Select all that apply." in panel
    assert "choice-check" in panel


def test_live_gemini_qna_ui_restricts_amendment_to_selected_or_other_choice():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "isOtherSelected" in panel
    assert "canUseAmendment" in panel
    assert "Other / not listed" in panel
    assert "Add details after choosing an answer." in panel
    assert "Other / not listed needs details before continuing." in panel


def test_live_gemini_qna_ui_shows_category_progress_and_collapsed_answer_history():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )

    assert "questionnaire" in api
    assert "draft_readiness" in api
    assert "active_category_id" in api
    assert "Overall readiness" in panel
    assert "Question areas" in panel
    assert "Active category" in panel
    assert "Working on:" in panel
    assert "Answered so far" in panel
    assert "Current understanding" in panel
    assert "Already understood" in panel
    assert "Completed areas" in panel
    assert "Suggested additions" in panel
    assert "questionnaire?.draft_readiness" in shell


def test_live_gemini_qna_ui_has_ready_handoff_and_optional_refinements():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "isQuestionnaireReady" in panel
    assert "Ready to draft" in panel
    assert "Optional refinements" in panel
    assert "optional-refinement-question" in panel
    assert "!isQuestionnaireReady && activeCategory" in panel


def test_live_gemini_qna_ui_keeps_confidence_in_collapsed_diagnostics():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    readiness = (WEB_SRC / "components" / "ReadinessPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "Analysis diagnostics" in panel
    assert "AI check:" in panel
    assert "AI check:" in readiness
    assert "{confidenceLabel} confidence" not in readiness


def test_live_gemini_qna_ui_uses_one_normal_percentage_and_word_statuses():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )
    readiness = (WEB_SRC / "components" / "ReadinessPanel.tsx").read_text(
        encoding="utf-8"
    )
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )

    assert "{questionnaire.draft_readiness.score}%" in panel
    assert "{category.progress}%" not in panel
    assert "questionAreaStatusLabel" in panel
    assert "typeof category.progress" not in readiness
    assert "statusLabel[category.status]" in readiness
    assert "analysisResponse ? null" in shell


def test_api_ts_sends_analysis_session_id():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "analysisSessionId?: string" in api
    assert "analysis_session_id: input.analysisSessionId ?? null" in api


def test_workspace_shell_regenerates_session_on_source_or_project_change():
    shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )

    assert "analysisSessionId" in shell
    assert "useState(() => crypto.randomUUID())" in shell
    assert "setAnalysisSessionId(crypto.randomUUID())" in shell
    assert "[sourceReferences.join(\",\"), driveRepo?.active_project_id]" in shell
    assert "analysisSessionId={analysisSessionId}" in shell


def test_analysis_panel_forwards_analysis_session_id():
    panel = (WEB_SRC / "components" / "AnalysisPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "analysisSessionId: string" in panel
    assert "analysisSessionId," in panel
    assert panel.count("analysisSessionId,") >= 3
