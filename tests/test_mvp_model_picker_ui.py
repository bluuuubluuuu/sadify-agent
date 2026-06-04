from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_model_catalog_api_contract_is_wired():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type ModelCatalogItem" in api
    assert "export type ModelCatalogResponse" in api
    assert "default: string" in api
    assert "models: ModelCatalogItem[]" in api
    assert "export async function listModels" in api
    assert "Promise<ModelCatalogResponse>" in api
    assert "/models" in api


def test_generation_requests_can_thread_selected_model():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "model?: string" in api
    assert "model: input.model ?? null" in api


def test_model_catalog_hook_loads_server_models_and_persists_selection():
    hook = (WEB_SRC / "lib" / "hooks" / "useModelCatalog.ts").read_text(
        encoding="utf-8"
    )

    assert "listModels" in hook
    assert "sadify:selectedModel" in hook
    assert 'const EMPTY_CATALOG: ModelCatalogResponse = { default: "", models: [] }' in hook
    assert 'useState("")' in hook
    assert "localStorage.getItem" in hook
    assert "localStorage.setItem" in hook
    assert "catalog.models.some" in hook
    assert "catalog.default" in hook
    assert "setSelectedModelState(next)" in hook
    assert "setIsLoaded(true)" in hook
    assert "gemini-2.5-flash" not in hook


def test_model_picker_renders_dynamic_catalog_and_hints():
    picker = (WEB_SRC / "components" / "chat" / "ModelPicker.tsx").read_text(
        encoding="utf-8"
    )
    chat = (WEB_SRC / "components" / "chat" / "ChatPanel.tsx").read_text(
        encoding="utf-8"
    )
    css = (WEB_SRC / "components" / "chat" / "chat.module.css").read_text(
        encoding="utf-8"
    )

    assert "catalog.models.map" in picker
    assert "model.hint" in picker
    assert "aria-label=\"Gemini model\"" in picker
    assert "catalog.models.length === 0" in picker
    assert "Loading models..." in picker
    assert "gemini-2.5-pro" not in picker
    assert "ModelPicker" in chat
    # Picker is a floating pill above the composer / ready bar (not a top bar).
    assert "modelFloat" in chat
    assert ".modelPill" in css
    assert ".modelMenu" in css
    assert ".modelFloat" in css


def test_answer_options_auto_collapse_and_manual_toggle_are_wired():
    chat = (WEB_SRC / "components" / "chat" / "ChatPanel.tsx").read_text(
        encoding="utf-8"
    )
    css = (WEB_SRC / "components" / "chat" / "chat.module.css").read_text(
        encoding="utf-8"
    )

    assert "const [optionsCollapsed, setOptionsCollapsed] = useState(false)" in chat
    assert "if (qna.isBusy)" in chat
    assert "setOptionsCollapsed(true)" in chat
    assert "questionText && questionText !== prevQuestionRef.current" in chat
    assert "setOptionsCollapsed(false)" in chat
    assert 'aria-expanded={!optionsCollapsed}' in chat
    assert "setOptionsCollapsed((value) => !value)" in chat
    assert "optionsCollapsed ? null" in chat
    assert ".optionsBar" in css
    assert ".optionsToggle" in css
    assert ".optionsReveal" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_workspace_threads_selected_model_into_qna_and_sad_preview():
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(
        encoding="utf-8"
    )
    qna = (WEB_SRC / "lib" / "hooks" / "useQnA.ts").read_text(encoding="utf-8")
    save = (WEB_SRC / "lib" / "hooks" / "useSadSave.ts").read_text(encoding="utf-8")

    assert "useModelCatalog" in workspace
    assert "models.isLoaded ? models.selectedModel : undefined" in workspace
    assert "selectedModel={models.selectedModel}" in workspace
    assert "onModelChange={models.setSelectedModel}" in workspace
    assert "model: selectedModel || undefined" in qna
    assert "model: selectedModel || undefined" in save
