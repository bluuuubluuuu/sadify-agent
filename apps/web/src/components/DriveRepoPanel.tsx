"use client";

import { useState } from "react";
import {
  connectDriveRepo,
  disconnectDriveRepo,
  type DriveRepoRecord,
} from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";
import {
  isGoogleOAuthConfigured,
  requestDriveAuthorizationCode,
} from "../lib/googleOAuth";

const DEFAULT_PROJECT_ID = "PROJ-LOCAL-001";

export function DriveRepoPanel() {
  const [repoName, setRepoName] = useState("SADify Project Repo");
  const [repo, setRepo] = useState<DriveRepoRecord | null>(null);
  const [message, setMessage] = useState(
    isGoogleOAuthConfigured()
      ? "Connect Drive only when you want to save project files."
      : "Configuration needed before live Google Drive connection.",
  );
  const [isBusy, setIsBusy] = useState(false);

  async function connectRepo() {
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setMessage("Sign in first, then connect Google Drive.");
      return;
    }
    if (!isGoogleOAuthConfigured()) {
      setMessage("Configuration needed: add NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID.");
      return;
    }

    setIsBusy(true);
    setMessage("Opening Google Drive permission...");
    try {
      const authorizationCode = await requestDriveAuthorizationCode();
      const idToken = await user.getIdToken();
      const connected = await connectDriveRepo({
        idToken,
        projectId: DEFAULT_PROJECT_ID,
        authorizationCode,
        repoFolderName: repoName,
        createNewRepo: true,
      });
      setRepo(connected);
      setMessage("Project repo connected. Saves are now allowed for this repo.");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not connect Google Drive.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function disconnectRepo() {
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
      setRepo(null);
      setMessage("Google Drive disconnected. Project saves are blocked.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Could not disconnect Google Drive.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="drive-panel" aria-label="Project repo connection">
      <div className="drive-copy">
        <p className="eyebrow">Project repo</p>
        <h2>Connect Google Drive</h2>
        <p>{message}</p>
      </div>

      <label className="drive-input">
        <span>Repo folder name</span>
        <input
          value={repoName}
          onChange={(event) => setRepoName(event.target.value)}
        />
      </label>

      <div className="drive-actions">
        <button
          type="button"
          className="primary-button"
          disabled={isBusy || !repoName.trim() || !isGoogleOAuthConfigured()}
          onClick={connectRepo}
        >
          Connect Google Drive
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={isBusy || !repo}
          onClick={disconnectRepo}
        >
          Disconnect Google Drive
        </button>
      </div>

      {!isGoogleOAuthConfigured() ? (
        <small className="drive-note">Configuration needed</small>
      ) : null}

      {repo ? (
        <dl className="drive-status">
          <div>
            <dt>Repo</dt>
            <dd>{repo.repo_folder_name}</dd>
          </div>
          <div>
            <dt>Grant</dt>
            <dd>{repo.grant_id}</dd>
          </div>
          <div>
            <dt>Save access</dt>
            <dd>{repo.saves_blocked ? "Blocked" : "Allowed"}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
