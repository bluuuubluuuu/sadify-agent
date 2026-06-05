from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_agent_api_contract_streams_and_approves():
    api = (WEB_SRC / "lib" / "api.ts").read_text(encoding="utf-8")

    assert "export type AgentEvent" in api
    assert "export type AgentFinalizeApiResponse" in api
    assert "export async function streamAgentFinalize" in api
    assert "/agent/finalize/stream" in api
    # fetch + ReadableStream (NOT EventSource — needs the auth header on approve).
    assert "response.body.getReader()" in api
    assert "new TextDecoder()" in api
    assert "EventSource" not in api
    assert "export async function approveAgentActions" in api
    assert "/agent/approve" in api
    assert "Authorization: `Bearer ${idToken}`" in api


def test_agent_finalize_hook_streams_events_then_approves():
    hook = (WEB_SRC / "lib" / "hooks" / "useAgentFinalize.ts").read_text(
        encoding="utf-8"
    )

    assert "streamAgentFinalize" in hook
    assert "approveAgentActions" in hook
    assert 'event.type === "status"' in hook
    assert "setEvents((previous) => [...previous, event])" in hook
    assert "result?.approval_id" in hook
    assert "getFirebaseAuth().currentUser" in hook
    assert "user.getIdToken()" in hook


def test_agent_timeline_renders_reasoning_and_approval():
    timeline = (WEB_SRC / "components" / "agent" / "AgentTimeline.tsx").read_text(
        encoding="utf-8"
    )
    css = (WEB_SRC / "components" / "agent" / "agent.module.css").read_text(
        encoding="utf-8"
    )

    # Timeline shows reasoning, not just tool names (GATE 4).
    assert "event.reasoning" in timeline
    assert "styles.reasoning" in timeline
    assert "events.map" in timeline
    assert 'status === "awaiting_approval"' in timeline
    assert "Approve" in timeline
    assert "onApprove" in timeline
    assert 'status === "asked_clarification"' in timeline
    assert 'status === "completed"' in timeline
    assert ".reasoning" in css
    assert ".timeline" in css
    assert ".approval" in css


def test_workspace_wires_agent_finalize_overlay():
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")
    preview = (WEB_SRC / "components" / "preview" / "PreviewPane.tsx").read_text(
        encoding="utf-8"
    )

    assert "useAgentFinalize" in workspace
    assert "analysisSessionId," in workspace
    assert "onFinalizeWithAgent={() => agent.finalize()}" in workspace
    assert "<AgentTimeline" in workspace
    assert "onApprove={() => agent.approve()}" in workspace
    # Additive: the manual save flow is untouched.
    assert "onSave={() => sadSave.save()}" in workspace
    assert "onFinalizeWithAgent?: () => void" in preview
    assert "Finalize with agent" in preview
