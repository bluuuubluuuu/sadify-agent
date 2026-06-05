"use client";

import { useState } from "react";
import {
  approveAgentActions,
  streamAgentFinalize,
  type AgentEvent,
  type AgentFinalizeStatus,
  type AgentProposedAction,
} from "../api";
import { getFirebaseAuth } from "../firebaseClient";

type AgentResult = {
  approval_id?: string;
  preview_id?: string;
  proposed_actions?: AgentProposedAction[];
  question?: string;
  actions?: Array<Record<string, unknown>>;
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
}: {
  analysisSessionId: string;
  selectedModel?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [status, setStatus] = useState<AgentFinalizeStatus | null>(null);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState("");

  async function finalize() {
    setIsOpen(true);
    setEvents([]);
    setStatus(null);
    setResult(null);
    setError("");
    setIsStreaming(true);
    try {
      await streamAgentFinalize(
        { analysisSessionId, model: selectedModel },
        (event) => {
          if (event.type === "status") {
            setStatus(event.status ?? null);
            setResult((event.result ?? null) as AgentResult | null);
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
      setEvents((previous) => [...previous, ...response.events]);
      setStatus(response.status);
      setResult((response.result ?? null) as AgentResult | null);
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
    isStreaming,
    isApproving,
    error,
    finalize,
    approve,
    close,
  };
}
