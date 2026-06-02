from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_live_gemini_qna_ui_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useQnA.ts",
        WEB_SRC / "components" / "chat" / "ChatPanel.tsx",
        WEB_SRC / "components" / "chat" / "AnswerChips.tsx",
        WEB_SRC / "components" / "chat" / "ReadinessPane.tsx",
        WEB_SRC / "lib" / "api.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_live_gemini_qna_api_contract_is_wired():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "analyzeRequirement" in api
    assert "/analysis/requirement" in api
    assert "readBackendError" in api
    assert "selection_mode" in api
    assert "questionnaire" in api
    assert "draft_readiness" in api
    assert "active_category_id" in api


def test_qna_engine_preserves_transport_and_fallback():
    qna = (WEB_SRC / "lib" / "hooks" / "useQnA.ts").read_text(encoding="utf-8")

    assert "continueWithAnswer" in qna
    assert "Previous answer:" in qna
    assert "Previous readiness:" in qna
    assert "selectedChoiceIds" in qna
    assert "amendmentText" in qna
    assert "toggleChoice" in qna
    assert "cleanRequirementText" in qna
    assert "appendKeptAnswer" in qna
    assert "Answer kept for SAD preview" in qna
    assert "Gemini could not prepare the next question" in qna
    assert "isFallbackAnalysis" in qna
    assert "Fallback question shown because Gemini output was invalid." in qna
    assert "isQuestionnaireReady" in qna
    assert 'selection_mode === "multiple"' in qna
    assert "isOtherSelected" in qna
    assert "canUseAmendment" in qna


def test_qna_choices_and_chat_render_question_flow():
    chips = (WEB_SRC / "components" / "chat" / "AnswerChips.tsx").read_text(encoding="utf-8")
    chat = (WEB_SRC / "components" / "chat" / "ChatPanel.tsx").read_text(encoding="utf-8")
    readiness = (WEB_SRC / "components" / "chat" / "ReadinessPane.tsx").read_text(encoding="utf-8")

    assert "choices" in chips
    assert "selectionMode" in chips
    assert "Select all that apply." in chips
    assert "Choose one." in chips
    assert "is_disabled" in chips
    assert "why_this_matters" in chat
    assert "Generate SAD preview" in chat
    assert "All required areas confirmed" in chat
    assert "What I understand so far" in readiness
    # D-wording (D-093): badge reads as evidence-grounding, not "confidence",
    # so high % + low grounding stops looking contradictory.
    assert "{confidence} evidence" in readiness
    assert "grounded in your uploaded source" in readiness


def test_api_ts_sends_analysis_session_id():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "analysisSessionId?: string" in api
    assert "analysis_session_id: input.analysisSessionId ?? null" in api


def test_workspace_regenerates_session_on_source_or_project_change():
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")

    assert "analysisSessionId" in workspace
    assert "useState(() => crypto.randomUUID())" in workspace
    assert "setAnalysisSessionId(crypto.randomUUID())" in workspace
    assert "driveRepo?.active_project_id" in workspace
    assert "sources.sourceReferences.join" in workspace
