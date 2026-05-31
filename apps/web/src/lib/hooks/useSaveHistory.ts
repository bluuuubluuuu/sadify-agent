"use client";

import { useEffect, useState } from "react";
import { listProjectSaves, type ProjectSavesResponse } from "../api";
import { getFirebaseAuth } from "../firebaseClient";

/**
 * Preserves ProjectHistoryPanel's load logic: reloads on active project or
 * refresh-key change, guards against unmounted updates, signed-out state.
 */
export function useSaveHistory(activeProjectId: string | null, refreshKey: number) {
  const [history, setHistory] = useState<ProjectSavesResponse | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState("Select a project to view saved SAD docs.");
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
            error instanceof Error ? error.message : "Could not load saved SAD history.",
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

  return {
    history,
    saves: history?.saves ?? [],
    isBusy,
    message,
    reload: () => setManualRefreshKey((current) => current + 1),
  };
}
