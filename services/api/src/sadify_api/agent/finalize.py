from dataclasses import replace
from typing import Any, Literal

from google.adk.agents import Agent
from google.adk.models import BaseLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from sadify_api.agent.approval import (
    ApprovalStore,
    ApprovalTokenInvalidError,
    WriteApproval,
    WriteApprovalRequiredError,
)
from sadify_api.agent.instruction import SADIFY_AGENT_INSTRUCTION
from sadify_api.agent.tools import (
    AgentDeps,
    build_agent_tool_functions,
    build_agent_tools,
)
from sadify_api.services.gemini_structured import log_adk_event_usage


def _model_name(model: object) -> str:
    if isinstance(model, str):
        return model
    return getattr(model, "model", model.__class__.__name__)

FinalizeStatus = Literal["asked_clarification", "awaiting_approval", "completed"]
REGENERATE_CAP = 2
DEFAULT_APPROVAL_STORE = ApprovalStore()


def build_finalize_agent(deps: AgentDeps, model: str | BaseLlm) -> Agent:
    return Agent(
        name="sadify_finalize",
        model=model,
        description="SADify analyst finalizer that chooses tools before finalizing.",
        instruction=SADIFY_AGENT_INSTRUCTION,
        tools=build_agent_tools(deps),
    )


def run_finalize(
    deps: AgentDeps,
    *,
    analysis_session_id: str,
    model: str | BaseLlm,
    approval_store: ApprovalStore | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    store = approval_store or DEFAULT_APPROVAL_STORE
    approval = _consume_approval(
        store,
        analysis_session_id=analysis_session_id,
        approval_id=approval_id,
    )
    tool_deps = _with_selected_model(replace(deps, write_approval=approval), model)
    agent = build_finalize_agent(tool_deps, model=model)
    session_service = InMemorySessionService()
    session_service.create_session_sync(
        app_name="sadify-api",
        user_id="sadify-finalizer",
        session_id=analysis_session_id,
    )
    runner = Runner(
        app_name="sadify-api",
        agent=agent,
        session_service=session_service,
    )
    events = []
    tool_results: list[tuple[str, dict[str, Any]]] = []
    try:
        for event in runner.run(
            user_id="sadify-finalizer",
            session_id=analysis_session_id,
            new_message=_finalize_message(deps, analysis_session_id, approval),
        ):
            log_adk_event_usage(_model_name(model), event)
            for function_response in event.get_function_responses():
                response = dict(function_response.response or {})
                tool_results.append((function_response.name, response))
                events.append(
                    {
                        "type": "tool",
                        "tool": function_response.name,
                        "summary": _tool_summary(function_response.name, response),
                    }
                )
    except WriteApprovalRequiredError as exc:
        new_approval_id = store.create(analysis_session_id, exc.proposed_actions)
        events.append(
            {
                "type": "tool",
                "tool": exc.tool_name,
                "summary": exc.message,
            }
        )
        return {
            "status": "awaiting_approval",
            "events": events,
            "result": _approval_result(
                approval_id=new_approval_id,
                error=exc,
                tool_results=tool_results,
            ),
        }

    events.extend(
        _ensure_draft_attempted(
            deps,
            tool_deps,
            analysis_session_id=analysis_session_id,
            tool_results=tool_results,
        )
    )
    status, result = _terminal_from_tool_results(
        tool_results,
        store=store,
        analysis_session_id=analysis_session_id,
    )
    return {
        "status": status,
        "events": events,
        "result": result,
    }


def _ensure_draft_attempted(
    deps: AgentDeps,
    tool_deps: AgentDeps,
    *,
    analysis_session_id: str,
    tool_results: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Deterministic safety-net so finalize never returns a phantom approval.

    Weak models sometimes call get_readiness and then stop without drafting.
    If the agent ended without ever attempting a draft or a clarification,
    produce one draft (and self-review) here. The LLM still drives the happy
    path; this only fills the gap so a draft is guaranteed whenever one is
    producible. If the draft is blocked by a missing basic, the terminal stays
    asked_clarification.
    """
    if any(name in ("generate_sad", "ask_clarification") for name, _ in tool_results):
        return []
    latest = deps.analysis_repository.latest_for_session(analysis_session_id)
    if latest is None:
        return []
    tool_functions = build_agent_tool_functions(tool_deps)
    generated = tool_functions.generate_sad(latest.analysis_id)
    tool_results.append(("generate_sad", generated))
    events = [
        {
            "type": "tool",
            "tool": "generate_sad",
            "summary": _tool_summary("generate_sad", generated),
            "reasoning": _tool_reasoning("generate_sad", generated),
        }
    ]
    preview_id = generated.get("preview_id")
    if preview_id:
        reviewed = tool_functions.review_sad(str(preview_id))
        tool_results.append(("review_sad", reviewed))
        events.append(
            {
                "type": "tool",
                "tool": "review_sad",
                "summary": _tool_summary("review_sad", reviewed),
                "reasoning": _tool_reasoning("review_sad", reviewed),
            }
        )
    return events


def stream_finalize_events(
    deps: AgentDeps,
    *,
    analysis_session_id: str,
    model: str | BaseLlm,
    approval_store: ApprovalStore | None = None,
):
    """Yield finalize activity events one at a time, ending in a terminal status.

    Each yielded item is a dict. Activity items use {"type": "tool"|"message",
    "tool", "summary", "reasoning"}; the final item is
    {"type": "status", "status", "result"}.
    """
    store = approval_store or DEFAULT_APPROVAL_STORE
    tool_deps = _with_selected_model(replace(deps, write_approval=None), model)
    agent = build_finalize_agent(tool_deps, model=model)
    session_service = InMemorySessionService()
    session_service.create_session_sync(
        app_name="sadify-api",
        user_id="sadify-finalizer",
        session_id=analysis_session_id,
    )
    runner = Runner(
        app_name="sadify-api",
        agent=agent,
        session_service=session_service,
    )
    tool_results: list[tuple[str, dict[str, Any]]] = []
    try:
        for event in runner.run(
            user_id="sadify-finalizer",
            session_id=analysis_session_id,
            new_message=_finalize_message(deps, analysis_session_id, None),
        ):
            log_adk_event_usage(_model_name(model), event)
            for function_response in event.get_function_responses():
                response = dict(function_response.response or {})
                tool_results.append((function_response.name, response))
                yield {
                    "type": "tool",
                    "tool": function_response.name,
                    "summary": _tool_summary(function_response.name, response),
                    "reasoning": _tool_reasoning(function_response.name, response),
                }
    except WriteApprovalRequiredError as exc:
        new_approval_id = store.create(analysis_session_id, exc.proposed_actions)
        yield {
            "type": "tool",
            "tool": exc.tool_name,
            "summary": exc.message,
            "reasoning": _approval_reasoning(),
        }
        yield {
            "type": "status",
            "status": "awaiting_approval",
            "result": _approval_result(
                approval_id=new_approval_id,
                error=exc,
                tool_results=tool_results,
            ),
        }
        return

    for extra_event in _ensure_draft_attempted(
        deps,
        tool_deps,
        analysis_session_id=analysis_session_id,
        tool_results=tool_results,
    ):
        yield extra_event

    status, result = _terminal_from_tool_results(
        tool_results,
        store=store,
        analysis_session_id=analysis_session_id,
    )
    if status == "awaiting_approval":
        yield {
            "type": "message",
            "tool": None,
            "summary": "Draft is ready — requesting your approval before saving.",
            "reasoning": _approval_reasoning(),
        }
    yield {"type": "status", "status": status, "result": result}


def _terminal_from_tool_results(
    tool_results: list[tuple[str, dict[str, Any]]],
    *,
    store: ApprovalStore,
    analysis_session_id: str,
) -> tuple[FinalizeStatus, dict[str, Any] | None]:
    approval_required = _latest_approval_required(tool_results)
    if approval_required is not None:
        proposed_actions = approval_required.get("proposed_actions", [])
        if not isinstance(proposed_actions, list):
            proposed_actions = []
        new_approval_id = store.create(analysis_session_id, proposed_actions)
        return "awaiting_approval", _approval_required_result(
            approval_id=new_approval_id,
            response=approval_required,
            tool_results=tool_results,
        )

    status, result = _final_status(tool_results)
    if status == "completed" and _is_ready_preview_result(result):
        new_approval_id = store.create(
            analysis_session_id,
            _save_and_wiki_actions(str(result["preview_id"])),
        )
        approval_result = dict(result)
        approval_result["approval_id"] = new_approval_id
        approval_result["proposed_actions"] = _save_and_wiki_actions(
            str(result["preview_id"])
        )
        return "awaiting_approval", approval_result
    return status, result


def run_approved_actions(
    deps: AgentDeps,
    *,
    analysis_session_id: str,
    approval_store: ApprovalStore,
    approval_id: str,
) -> dict[str, Any]:
    approval = approval_store.get(analysis_session_id, approval_id)
    if approval is None:
        raise ApprovalTokenInvalidError("Approval token is missing or already used.")

    tool_functions = build_agent_tool_functions(
        replace(deps, write_approval=approval),
    )
    actions = _ordered_actions(approval.actions)
    results = []
    for action in actions:
        action_id = str(action.get("id") or "")
        try:
            if action_id == "save_to_drive":
                preview_id = str(action.get("preview_id") or "")
                if not preview_id:
                    raise ApprovalTokenInvalidError(
                        "Approved save action has no preview."
                    )
                response = tool_functions.save_to_drive(preview_id)
            elif action_id == "update_wiki":
                response = tool_functions.update_wiki(False)
            elif action_id == "overwrite_wiki":
                response = tool_functions.update_wiki(True)
            else:
                raise ApprovalTokenInvalidError(f"Unknown approved action: {action_id}")
        except WriteApprovalRequiredError as exc:
            approval_store.consume(analysis_session_id, approval_id)
            new_approval_id = approval_store.create(
                analysis_session_id,
                exc.proposed_actions,
            )
            conflict_result = _approval_result(
                approval_id=new_approval_id,
                error=exc,
                tool_results=[],
            )
            if results:
                conflict_result["completed_actions"] = results
            return {
                "status": "awaiting_approval",
                "events": [
                    {
                        "type": "tool",
                        "tool": exc.tool_name,
                        "summary": exc.message,
                    }
                ],
                "result": conflict_result,
            }

        if response.get("status") == "error":
            error_result = {
                "approval_id": approval_id,
                "proposed_actions": approval.actions,
                "error": {
                    "code": response.get("code"),
                    "message": response.get("message"),
                },
            }
            if results:
                error_result["completed_actions"] = results
            return {
                "status": "awaiting_approval",
                "events": [
                    {
                        "type": "tool",
                        "tool": action_id,
                        "summary": str(
                            response.get("message") or "Approved action failed."
                        ),
                    }
                ],
                "result": error_result,
            }
        results.append({"tool": action_id, **response})

    approval_store.consume(analysis_session_id, approval_id)
    return {
        "status": "completed",
        "events": [
            {
                "type": "tool",
                "tool": result["tool"],
                "summary": _tool_summary(result["tool"], result),
            }
            for result in results
        ],
        "result": {"actions": results},
    }


def _consume_approval(
    store: ApprovalStore,
    *,
    analysis_session_id: str,
    approval_id: str | None,
) -> WriteApproval | None:
    if approval_id is None:
        return None
    approval = store.consume(analysis_session_id, approval_id)
    if approval is None:
        raise ApprovalTokenInvalidError("Approval token is missing or already used.")
    return approval


def _ordered_actions(actions: list[dict[str, object]]) -> list[dict[str, object]]:
    order = {"save_to_drive": 0, "update_wiki": 1, "overwrite_wiki": 1}
    return sorted(actions, key=lambda action: order.get(str(action.get("id")), 99))


def _is_ready_preview_result(result: dict[str, Any] | None) -> bool:
    return isinstance(result, dict) and bool(result.get("preview_id"))


def _save_and_wiki_actions(preview_id: str) -> list[dict[str, object]]:
    return [
        {
            "id": "save_to_drive",
            "label": "Save SAD to Google Drive",
            "preview_id": preview_id,
        },
        {
            "id": "update_wiki",
            "label": "Update project wiki",
            "preview_id": preview_id,
        },
    ]


def _with_selected_model(deps: AgentDeps, model: str | BaseLlm) -> AgentDeps:
    if isinstance(model, str):
        return replace(
            deps,
            selected_model=model,
            max_sad_generations=REGENERATE_CAP + 1,
        )
    return replace(deps, max_sad_generations=REGENERATE_CAP + 1)


def _finalize_message(
    deps: AgentDeps,
    analysis_session_id: str,
    approval: WriteApproval | None,
) -> types.Content:
    latest = deps.analysis_repository.latest_for_session(analysis_session_id)
    latest_analysis_id = latest.analysis_id if latest is not None else ""
    prompt = (
        "Finalize the SADify analysis session by choosing the right tools.\n"
        f"analysis_session_id: {analysis_session_id}\n"
        f"latest_analysis_id: {latest_analysis_id}\n"
        "The existing Q&A answers are the source of truth. Trust them and do "
        "NOT re-ask anything the user already answered. "
        "First inspect readiness when an analysis id is available, then you MUST "
        "call generate_sad — never stop after only checking readiness. If "
        "generate_sad reports it is blocked by a missing "
        "basic, stop and return that one clarification. Otherwise a draft "
        "exists: call review_sad on it. If review_sad says regenerate, you may "
        "call generate_sad again and review the new draft. If it says proceed, "
        "tighten, or ask, stop with the best draft — minor gaps belong in the "
        "draft's open questions, not in a new question to the user. "
        "Do not call extract_dev_tasks during this finalize/save flow; "
        "developer tasks are a separate user-requested step after an approved "
        "SAD preview. "
        "The backend will request explicit approval after a ready draft. Do not "
        "write to Drive, wiki, or GitHub without approval."
    )
    if approval is not None:
        prompt += (
            "\nApproval granted for these actions only:\n"
            f"{approval.actions}\n"
            "Execute only approved write tools, then stop."
        )
    return types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )


def _final_status(
    tool_results: list[tuple[str, dict[str, Any]]],
) -> tuple[FinalizeStatus, dict[str, Any] | None]:
    write_actions = [
        {"tool": tool_name, **response}
        for tool_name, response in tool_results
        if tool_name in ("save_to_drive", "update_wiki")
    ]
    if write_actions:
        return "completed", {"actions": write_actions}

    latest_review = _latest_tool_result(tool_results, "review_sad")
    latest_preview = _latest_tool_result(tool_results, "generate_sad")
    has_draft = latest_preview is not None and bool(latest_preview.get("preview_id"))

    # Collaborative model (Option A): the agent trusts the completed Q&A and
    # finalizes whenever it could produce a draft. A draft wins over a stray
    # ask_clarification, and a "tighten"/"ask" self-review folds its gaps into
    # the SAD's open questions instead of re-interrogating the user. The ONLY
    # genuine block is when no draft exists (generate_sad was blocked by a
    # missing basic, or the agent only asked without drafting).
    if not has_draft:
        for tool_name, response in reversed(tool_results):
            if tool_name == "ask_clarification":
                return "asked_clarification", response
            if tool_name == "review_sad" and response.get("verdict") == "ask":
                return "asked_clarification", response
        if latest_preview is not None:
            # generate_sad ran but was blocked (missing basics, no preview_id).
            return "asked_clarification", latest_preview
        return "awaiting_approval", None

    result = dict(latest_preview)
    if latest_review is not None:
        result["review"] = latest_review
        verdict = latest_review.get("verdict")
        if latest_review.get("regenerate_cap_reached") or verdict in ("tighten", "ask"):
            result["open_questions"] = _open_questions_with_review_issues(
                result.get("open_questions", []),
                latest_review,
            )
    return "completed", result


def _approval_result(
    *,
    approval_id: str,
    error: WriteApprovalRequiredError,
    tool_results: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "approval_id": approval_id,
        "proposed_actions": error.proposed_actions,
    }
    if error.preview_id:
        result["preview_id"] = error.preview_id
    else:
        latest_preview = _latest_tool_result(tool_results, "generate_sad")
        if latest_preview is not None and latest_preview.get("preview_id"):
            result["preview_id"] = latest_preview["preview_id"]
    if error.changed_files is not None:
        result["changed_files"] = error.changed_files
    return result


def _approval_required_result(
    *,
    approval_id: str,
    response: dict[str, Any],
    tool_results: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "approval_id": approval_id,
        "proposed_actions": response.get("proposed_actions", []),
    }
    preview_id = response.get("preview_id")
    if preview_id:
        result["preview_id"] = preview_id
    else:
        latest_preview = _latest_tool_result(tool_results, "generate_sad")
        if latest_preview is not None and latest_preview.get("preview_id"):
            result["preview_id"] = latest_preview["preview_id"]
    changed_files = response.get("changed_files")
    if changed_files is not None:
        result["changed_files"] = changed_files
    return result


def _latest_approval_required(
    tool_results: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    for _tool_name, response in reversed(tool_results):
        if response.get("approval_required"):
            return response
    return None


def _latest_tool_result(
    tool_results: list[tuple[str, dict[str, Any]]],
    tool_name: str,
) -> dict[str, Any] | None:
    for candidate_name, response in reversed(tool_results):
        if candidate_name == tool_name:
            return response
    return None


def _open_questions_with_review_issues(
    open_questions: Any,
    review: dict[str, Any],
) -> list[str]:
    merged = list(open_questions) if isinstance(open_questions, list) else []
    for issue in review.get("issues", []):
        if not isinstance(issue, dict):
            continue
        message = str(issue.get("message") or "").strip()
        if message:
            merged.append(f"Review remaining issue: {message}")
    return merged


def _tool_summary(tool_name: str, response: dict[str, Any]) -> str:
    if tool_name == "get_readiness":
        label = response.get("label", "Readiness checked")
        score = response.get("score")
        confidence = response.get("confidence")
        if score is not None and confidence:
            return f"{label}: {score}% readiness, {confidence} confidence."
        return str(label)
    if tool_name == "ask_clarification":
        return str(response.get("question") or "Asked one clarification question.")
    if tool_name == "generate_sad":
        preview_id = response.get("preview_id")
        if preview_id:
            return f"Generated SAD preview {preview_id}."
        return "Generated a SAD preview."
    if tool_name == "review_sad":
        verdict = response.get("verdict", "reviewed")
        issues = response.get("issues", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        return f"Reviewed SAD draft: {verdict} ({issue_count} issues)."
    if tool_name == "save_to_drive":
        if response.get("status") == "saved":
            return f"Saved SAD preview {response.get('preview_id')} to Drive."
        return str(response.get("message") or "SAD save did not complete.")
    if tool_name == "update_wiki":
        if response.get("status") == "updated":
            return f"Updated wiki ({response.get('file_count', 0)} files)."
        return str(response.get("message") or "Wiki update did not complete.")
    return f"Ran {tool_name}."


def _tool_reasoning(tool_name: str, response: dict[str, Any]) -> str:
    """Explain WHY the agent took this step, derived from the tool result."""
    if tool_name == "get_readiness":
        score = response.get("score")
        confidence = response.get("confidence")
        gaps = response.get("gaps")
        gap_count = len(gaps) if isinstance(gaps, list) else 0
        head = f"Requirement readiness {score}% with {confidence} confidence"
        if gap_count:
            return f"{head}; {gap_count} area(s) still open — judging if that is enough to draft."
        return f"{head}; the basics are covered — strong enough to draft."
    if tool_name == "ask_clarification":
        return (
            "Not confident enough to draft yet — asking one grounded question "
            "to close the most important gap instead of guessing."
        )
    if tool_name == "generate_sad":
        if response.get("error") == "sad_preview_blocked":
            return "Cannot draft yet — basic facts are still missing; flagging them."
        sections = response.get("sections")
        section_count = len(sections) if isinstance(sections, list) else 0
        return f"Requirement is ready — drafted a SAD with {section_count} section(s) from the analysis."
    if tool_name == "review_sad":
        verdict = response.get("verdict", "reviewed")
        issues = response.get("issues", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        if response.get("regenerate_cap_reached"):
            return (
                f"Self-review still flags {issue_count} issue(s) but the regeneration "
                "cap is reached — surfacing them as open questions instead of looping."
            )
        if verdict == "proceed":
            return f"Self-review passed ({issue_count} issue(s)) — this draft is good to finalize."
        if verdict == "tighten":
            return f"Self-review found {issue_count} minor gap(s) — keeping this draft but flagging them."
        if verdict == "regenerate":
            return f"Self-review found {issue_count} weak/ungrounded point(s) — regenerating a stronger draft."
        if verdict == "ask":
            return f"Self-review says the draft needs a human answer ({issue_count} issue(s)) — asking instead of finalizing."
        return f"Reviewed the draft: {verdict}."
    if tool_name in ("save_to_drive", "update_wiki"):
        return "Executing an approved write."
    return ""


def _approval_reasoning() -> str:
    return (
        "The draft is strong enough to finalize — pausing for your explicit "
        "approval before writing anything to Drive or the wiki."
    )
