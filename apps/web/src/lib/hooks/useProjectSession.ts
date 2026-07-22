"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  getProjectSession,
  putProjectSession,
  type ProjectSessionSnapshot,
} from "../api";
import { getFirebaseAuth } from "../firebaseClient";

const WRITE_DELAY_MS = 800;

export function useProjectSession() {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancel = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const writeDebounced = useCallback(
    (
      projectId: string,
      snapshot: ProjectSessionSnapshot,
      isCurrent: (projectId: string) => boolean,
    ) => {
      cancel();
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        if (!isCurrent(projectId)) {
          return;
        }
        void (async () => {
          try {
            const user = getFirebaseAuth().currentUser;
            if (!user) {
              return;
            }
            const idToken = await user.getIdToken();
            if (!isCurrent(projectId)) {
              return;
            }
            await putProjectSession(idToken, projectId, snapshot);
          } catch (error) {
            console.warn("Could not persist the project session snapshot.", error);
          }
        })();
      }, WRITE_DELAY_MS);
    },
    [cancel],
  );

  const restore = useCallback(async (projectId: string) => {
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      return { projectId, snapshot: null };
    }
    const idToken = await user.getIdToken();
    const snapshot = await getProjectSession(idToken, projectId);
    return { projectId, snapshot };
  }, []);

  useEffect(() => cancel, [cancel]);

  return { writeDebounced, cancel, restore };
}
