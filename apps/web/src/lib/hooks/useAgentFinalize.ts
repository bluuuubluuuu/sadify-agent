"use client";

import { useState } from "react";
import {
  approveAgentActions,
  streamAgentFinalize,
  type AgentEvent,
  type AgentFinalizeStatus,
  type AgentProposedAction,
  type SadPreviewResponse,
  type SadSaveRecord,
  type WikiUpdateResponse,
} from "../api";
import { getFirebaseAuth } from "../firebaseClient";
import type { AdoptedAgentSave } from "./useSadSave";

type AgentResult = {
  approval_id?: string;
  proposed_actions?: AgentProposedAction[];
  question?: string;
  preview_id?: string;
  preview?: SadPreviewResponse;
  actions?: Array<Record<string, unknown>>;
  completed_actions?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

/**
 * Drives the agent Finalize flow: streams reason/act/reflect activity from
 * POST /agent/finalize/stream (fetch + ReadableStream, NOT EventSource — the
 * stream needs the Firebase Authorization header), then runs the deterministic
 * approved save via POST /agent/approve. Additive: the manual preview/save flow
 * is untouched.
 */
export function useAgentFinalize({
  analysisSessionId,
  selectedModel,
  onSaved,
}: {
  analysisSessionId: string;
  selectedModel?: string;
  onSaved?: (savedSad: AdoptedAgentSave | null) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [status, setStatus] = useState<AgentFinalizeStatus | null>(null);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState("");
  const [lastDraft, setLastDraft] = useState<AgentResult | null>(null);
  const [savedSad, setSavedSad] = useState<AdoptedAgentSave | null>(null);

  async function finalize() {
    setIsOpen(true);
    setEvents([]);
    setStatus(null);
    setResult(null);
    setLastDraft(null);
    setSavedSad(null);
    setError("");
    setIsStreaming(true);
    try {
      await streamAgentFinalize(
        { analysisSessionId, model: selectedModel },
        (event) => {
          if (event.type === "status") {
            const nextResult = (event.result ?? null) as AgentResult | null;
            setStatus(event.status ?? null);
            setResult(nextResult);
            if (hasPreviewPayload(nextResult)) {
              setLastDraft(nextResult);
            }
            return;
          }
          setEvents((previous) => [...previous, event]);
        },
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The agent run failed.");
    } finally {
      setIsStreaming(false);
    }
  }

  async function approve() {
    const approvalId = result?.approval_id;
    if (!approvalId) {
      return;
    }
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setError("Sign in with Google before approving the save.");
      return;
    }
    setIsApproving(true);
    setError("");
    try {
      const idToken = await user.getIdToken();
      const response = await approveAgentActions(
        { analysisSessionId, approvalId, model: selectedModel },
        idToken,
      );
      const previousDraft = hasPreviewPayload(result) ? result : lastDraft;
      const nextResult = (response.result ?? null) as AgentResult | null;
      const freshSave = adoptedSaveFromAgentResults(previousDraft, nextResult);
      // A later approval (e.g. wiki-overwrite re-approval) returns ONLY the wiki
      // action — carry the already-saved SAD forward and attach this turn's wiki
      // record so the "Wiki updated" panel appears alongside the saved SAD.
      const wikiThisTurn = wikiRecordFromActions(nextResult);
      const adopted: AdoptedAgentSave | null =
        freshSave ??
        (savedSad
          ? { ...savedSad, wiki: wikiThisTurn ?? savedSad.wiki ?? null }
          : null);
      setEvents((previous) => [...previous, ...response.events]);
      setStatus(response.status);
      setResult(nextResult);
      if (adopted) {
        setSavedSad(adopted);
      }
      // Refresh save history whenever a write landed — a wiki conflict returns
      // awaiting_approval but the SAD save already succeeded.
      const wroteSomething =
        response.status === "completed" ||
        Boolean(nextResult?.completed_actions);
      if (wroteSomething) {
        onSaved?.(adopted);
      }
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "The approved save failed.",
      );
    } finally {
      setIsApproving(false);
    }
  }

  function close() {
    setIsOpen(false);
  }

  return {
    isOpen,
    events,
    status,
    result,
    savedSad,
    isStreaming,
    isApproving,
    error,
    finalize,
    approve,
    close,
  };
}

function hasPreviewPayload(result: AgentResult | null): result is AgentResult & {
  preview_id: string;
  preview: SadPreviewResponse;
} {
  return (
    typeof result?.preview_id === "string" &&
    Boolean(result.preview_id) &&
    isRecord(result.preview)
  );
}

function adoptedSaveFromAgentResults(
  draft: AgentResult | null,
  writeResult: AgentResult | null,
): AdoptedAgentSave | null {
  if (!hasPreviewPayload(draft)) {
    return null;
  }
  const save = savedAction(writeResult);
  const record = save?.record;
  if (!isRecord(record)) {
    return null;
  }
  return {
    previewId: draft.preview_id,
    preview: draft.preview,
    record: record as SadSaveRecord,
    wiki: wikiRecordFromActions(writeResult),
  };
}

function wikiRecordFromActions(
  result: AgentResult | null,
): WikiUpdateResponse | null {
  const actions = [...(result?.actions ?? []), ...(result?.completed_actions ?? [])];
  const wikiAction = actions.find(
    (action) => action.tool === "update_wiki" || action.tool === "overwrite_wiki",
  );
  const wiki = wikiAction?.wiki;
  return isRecord(wiki) ? (wiki as WikiUpdateResponse) : null;
}

function savedAction(result: AgentResult | null): Record<string, unknown> | null {
  const actions = [...(result?.actions ?? []), ...(result?.completed_actions ?? [])];
  return actions.find((action) => action.tool === "save_to_drive") ?? null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
