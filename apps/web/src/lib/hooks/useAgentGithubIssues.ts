"use client";

import { useState } from "react";
import {
  approveAgentGithubIssues,
  BackendApiError,
  prepareAgentGithubIssues,
  type AgentEvent,
  type AgentFinalizeStatus,
  type AgentProposedAction,
} from "../api";
import { getFirebaseAuth } from "../firebaseClient";

type AgentGithubResult = {
  approval_id?: string;
  preview_id?: string;
  repo?: string;
  proposed_actions?: AgentProposedAction[];
  issues?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

const SETUP_ERROR_CODES = new Set([
  "GITHUB_MCP_DISABLED",
  "DEV_TASKS_MODEL_UNAVAILABLE",
]);

export function useAgentGithubIssues({
  analysisSessionId,
  selectedModel,
}: {
  analysisSessionId: string;
  selectedModel?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [status, setStatus] = useState<AgentFinalizeStatus | null>(null);
  const [result, setResult] = useState<AgentGithubResult | null>(null);
  const [isPreparing, setIsPreparing] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState("");
  const [setupNotice, setSetupNotice] = useState("");
  // Pasted PAT — held in memory only for this session, never persisted.
  const [githubToken, setGithubToken] = useState("");

  async function prepare(previewId: string | null, repo?: string | null) {
    if (!previewId) {
      setSetupNotice("Generate and save a SAD preview before preparing GitHub issues.");
      return;
    }
    setIsPreparing(true);
    setError("");
    setSetupNotice("");
    try {
      const response = await prepareAgentGithubIssues({
        analysisSessionId,
        previewId,
        repo: repo ?? undefined,
        model: selectedModel,
      });
      setEvents(response.events);
      setStatus(response.status);
      setResult((response.result ?? null) as AgentGithubResult | null);
      setIsOpen(true);
    } catch (caught) {
      if (caught instanceof BackendApiError && SETUP_ERROR_CODES.has(caught.code ?? "")) {
        setSetupNotice(caught.message);
        setIsOpen(false);
      } else {
        setError(
          caught instanceof Error ? caught.message : "SADify could not prepare GitHub issues.",
        );
        setIsOpen(true);
      }
    } finally {
      setIsPreparing(false);
    }
  }

  async function approve() {
    const approvalId = result?.approval_id;
    if (!approvalId) {
      return;
    }
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setError("Sign in with Google before creating GitHub issues.");
      return;
    }
    setIsApproving(true);
    setError("");
    try {
      const idToken = await user.getIdToken();
      const response = await approveAgentGithubIssues(
        {
          analysisSessionId,
          approvalId,
          githubToken: githubToken || undefined,
          model: selectedModel,
        },
        idToken,
      );
      setEvents((previous) => [...previous, ...response.events]);
      setStatus(response.status);
      setResult((response.result ?? null) as AgentGithubResult | null);
    } catch (caught) {
      if (isAuthError(caught)) {
        setError("Sign in with Google before creating GitHub issues.");
      } else {
        setError(
          caught instanceof Error ? caught.message : "SADify could not create GitHub issues.",
        );
      }
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
    isPreparing,
    isApproving,
    error,
    setupNotice,
    githubToken,
    setGithubToken,
    hasToken: githubToken.trim().length > 0,
    prepare,
    approve,
    close,
  };
}

function isAuthError(error: unknown) {
  return error instanceof BackendApiError && (error.status === 401 || error.status === 403);
}
