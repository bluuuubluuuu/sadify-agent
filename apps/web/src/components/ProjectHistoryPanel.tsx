"use client";

import { useEffect, useState } from "react";
import {
  listProjectSaves,
  type ProjectSavesResponse,
  type SadSaveSummary,
} from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";

type Props = {
  activeProjectId: string | null;
  refreshKey: number;
};

function formatSavedAt(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ProjectHistoryPanel({ activeProjectId, refreshKey }: Props) {
  const [history, setHistory] = useState<ProjectSavesResponse | null>(null);
  const [message, setMessage] = useState(
    "Select a project to view saved SAD docs.",
  );
  const [isBusy, setIsBusy] = useState(false);
  const [manualRefreshKey, setManualRefreshKey] = useState(0);

  useEffect(() => {
    if (!activeProjectId) {
      setHistory(null);
      setMessage("Select a project to view saved SAD docs.");
      return;
    }

    const projectId = activeProjectId;
    let isMounted = true;

    async function loadHistory() {
      const user = getFirebaseAuth().currentUser;
      if (!user) {
        if (isMounted) {
          setHistory(null);
          setMessage("Sign in to view project history.");
        }
        return;
      }

      if (isMounted) {
        setIsBusy(true);
        setMessage("Loading saved SAD docs...");
      }
      try {
        const idToken = await user.getIdToken();
        const response = await listProjectSaves(idToken, projectId);
        if (!isMounted) {
          return;
        }
        setHistory(response);
        setMessage(
          response.saves.length
            ? `${response.saves.length} saved SAD doc(s).`
            : "No saves yet.",
        );
      } catch (error) {
        if (isMounted) {
          setHistory(null);
          setMessage(
            error instanceof Error
              ? error.message
              : "Could not load saved SAD history.",
          );
        }
      } finally {
        if (isMounted) {
          setIsBusy(false);
        }
      }
    }

    loadHistory();

    return () => {
      isMounted = false;
    };
  }, [activeProjectId, refreshKey, manualRefreshKey]);

  const saves: SadSaveSummary[] = history?.saves ?? [];

  return (
    <section className="drive-panel" aria-label="Project save history">
      <div className="drive-copy">
        <p className="eyebrow">Save history</p>
        <h2>{history?.project_name ?? "Project SAD docs"}</h2>
        <p>{message}</p>
      </div>

      <div className="drive-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={isBusy || !activeProjectId}
          onClick={() => setManualRefreshKey((current) => current + 1)}
        >
          Refresh
        </button>
      </div>

      {activeProjectId && !saves.length ? (
        <small className="drive-note">No saves yet.</small>
      ) : null}

      {saves.length ? (
        <ul className="source-list">
          {saves.map((save) => (
            <li key={`${save.preview_id}-${save.save_id}`}>
              <strong>{save.save_id}</strong>
              <span>{formatSavedAt(save.created_at)}</span>
              <small>{save.doc_path}</small>
              {save.doc_url ? (
                <a
                  href={save.doc_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open Doc
                </a>
              ) : null}
              <p>{save.change_summary}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
