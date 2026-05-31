"use client";

import { useState } from "react";
import { connectDriveRepo, disconnectDriveRepo, type DriveRepoRecord } from "../api";
import { getFirebaseAuth } from "../firebaseClient";
import { isGoogleOAuthConfigured, requestDriveAuthorizationCode } from "../googleOAuth";

const DEFAULT_PROJECT_ID = "PROJ-LOCAL-001";

/**
 * Preserves DriveRepoPanel's connect/disconnect logic exactly: live OAuth code
 * when configured, else the local-dev stub code; same default project id and
 * connectDriveRepo payload.
 */
export function useDriveRepo(onRepoChanged: (repo: DriveRepoRecord | null) => void) {
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function connect(repoFolderName = "SADify Project Repo") {
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setMessage("Sign in first, then connect Google Drive.");
      return;
    }
    setIsBusy(true);
    setMessage("Opening Google Drive permission...");
    try {
      const authorizationCode = isGoogleOAuthConfigured()
        ? await requestDriveAuthorizationCode()
        : "LOCAL-DEV-STUB-CODE";
      const idToken = await user.getIdToken();
      const connected = await connectDriveRepo({
        idToken,
        projectId: DEFAULT_PROJECT_ID,
        authorizationCode,
        repoFolderName,
        createNewRepo: true,
      });
      onRepoChanged(connected);
      setMessage("Project repo connected. Saves are now allowed for this repo.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not connect Google Drive.");
    } finally {
      setIsBusy(false);
    }
  }

  async function disconnect() {
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setMessage("Sign in first.");
      return;
    }
    setIsBusy(true);
    setMessage("Disconnecting Google Drive...");
    try {
      const idToken = await user.getIdToken();
      await disconnectDriveRepo(idToken);
      onRepoChanged(null);
      setMessage("Google Drive disconnected. Project saves are blocked.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not disconnect Google Drive.");
    } finally {
      setIsBusy(false);
    }
  }

  return { isBusy, message, connect, disconnect, oauthConfigured: isGoogleOAuthConfigured() };
}
