"use client";

import { useMemo, useState } from "react";
import {
  createGuestDraft,
  migrateGuestDraft,
  type GuestDraftMigrationResponse,
  type GuestDraftRecord,
} from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";
import { isFirebaseConfigured } from "../lib/firebaseConfig";

function getGuestSessionId() {
  if (typeof window === "undefined") {
    return "server-render";
  }

  const key = "sadify.guestSessionId";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }

  const nextValue = `guest-${crypto.randomUUID()}`;
  window.localStorage.setItem(key, nextValue);
  return nextValue;
}

export function DraftPanel() {
  const guestSessionId = useMemo(() => getGuestSessionId(), []);
  const [requirementText, setRequirementText] = useState(
    "Need to validate an operational workflow idea.",
  );
  const [draft, setDraft] = useState<GuestDraftRecord | null>(null);
  const [migration, setMigration] = useState<GuestDraftMigrationResponse | null>(null);
  const [message, setMessage] = useState("Start as guest, then copy after sign-in.");
  const [isBusy, setIsBusy] = useState(false);

  async function startGuestDraft() {
    setIsBusy(true);
    setMessage("Creating guest draft...");
    try {
      const createdDraft = await createGuestDraft({
        guestSessionId,
        requirementText,
      });
      setDraft(createdDraft);
      setMigration(null);
      setMessage("Guest draft saved locally in the backend fake store.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Guest draft failed.");
    } finally {
      setIsBusy(false);
    }
  }

  async function copyDraftToSignedInProject() {
    if (!draft) {
      setMessage("Start guest draft first.");
      return;
    }

    if (!isFirebaseConfigured()) {
      setMessage("Sign in config is needed before copying this draft.");
      return;
    }

    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setMessage("Sign in first, then copy this guest draft.");
      return;
    }

    setIsBusy(true);
    setMessage("Copying guest draft...");
    try {
      const idToken = await user.getIdToken();
      const copied = await migrateGuestDraft(draft.guest_draft_id, idToken);
      setDraft(copied.guest_draft);
      setMigration(copied);
      setMessage(copied.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Migration failed.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="draft-panel" aria-label="Guest draft migration">
      <div className="draft-panel-copy">
        <p className="eyebrow">Draft</p>
        <h2>Keep the idea as guest, then copy it after sign-in.</h2>
        <p>{message}</p>
      </div>

      <label className="draft-input">
        <span>What are we validating?</span>
        <textarea
          value={requirementText}
          onChange={(event) => setRequirementText(event.target.value)}
        />
      </label>

      <div className="draft-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={isBusy}
          onClick={startGuestDraft}
        >
          Start guest draft
        </button>
        <button
          type="button"
          className="primary-button"
          disabled={isBusy || !draft}
          onClick={copyDraftToSignedInProject}
        >
          Copy to signed-in project
        </button>
      </div>

      {draft ? (
        <dl className="draft-status">
          <div>
            <dt>Guest draft</dt>
            <dd>{draft.guest_draft_id}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{draft.status}</dd>
          </div>
          <div>
            <dt>Guest draft kept for audit</dt>
            <dd>{draft.migrated_to_project_id ?? "Not copied yet"}</dd>
          </div>
        </dl>
      ) : null}

      {migration ? (
        <p className="draft-link">
          Project copy {migration.project.project_id} links back to{" "}
          {migration.project.source_guest_draft_id}.
        </p>
      ) : null}
    </section>
  );
}
