"use client";

import { onAuthStateChanged, type User } from "firebase/auth";
import { useEffect, useState } from "react";
import { verifyAuthSession, type AuthenticatedUser } from "../lib/api";
import {
  ensureLocalAuthPersistence,
  getFirebaseAuth,
  signInWithGoogle,
  signOutOfGoogle,
} from "../lib/firebaseClient";
import { isFirebaseConfigured } from "../lib/firebaseConfig";

type SessionState = "guest" | "config_needed" | "signed_out" | "signing_in" | "signed_in";

export function AuthPanel() {
  const [sessionState, setSessionState] = useState<SessionState>(
    isFirebaseConfigured() ? "signed_out" : "config_needed",
  );
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [backendUser, setBackendUser] = useState<AuthenticatedUser | null>(null);
  const [message, setMessage] = useState(
    isFirebaseConfigured()
      ? "Sign in when you want to save this draft to a project repo."
      : "Firebase config needed before Google sign-in can run.",
  );

  useEffect(() => {
    if (!isFirebaseConfigured()) {
      return;
    }

    const auth = getFirebaseAuth();
    void ensureLocalAuthPersistence(auth);

    return onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user);
      if (!user) {
        setBackendUser(null);
        setSessionState("signed_out");
        setMessage("Sign in when you want to save this draft to a project repo.");
        return;
      }

      try {
        const idToken = await user.getIdToken();
        const session = await verifyAuthSession(idToken);
        setBackendUser(session.user);
        setSessionState("signed_in");
        setMessage("Signed in. Your session will stay live on this browser.");
      } catch (error) {
        setBackendUser(null);
        setSessionState("signed_out");
        setMessage(error instanceof Error ? error.message : "Session verification failed.");
      }
    });
  }, []);

  async function startGoogleSession() {
    if (!isFirebaseConfigured()) {
      setSessionState("config_needed");
      setMessage("Firebase config needed before Google sign-in can run.");
      return;
    }

    setSessionState("signing_in");
    setMessage("Opening Google sign-in...");
    try {
      await signInWithGoogle();
    } catch (error) {
      setSessionState("signed_out");
      setMessage(error instanceof Error ? error.message : "Google sign-in failed.");
    }
  }

  async function endGoogleSession() {
    try {
      await signOutOfGoogle();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sign out failed.");
    }
  }

  const signedInName = backendUser?.display_name ?? firebaseUser?.displayName;
  const signedInEmail = backendUser?.email ?? firebaseUser?.email;

  return (
    <section className="auth-panel" aria-label="Session controls">
      <div>
        <p className="eyebrow">Session</p>
        <strong>
          {sessionState === "signed_in"
            ? signedInName || signedInEmail || "Signed in"
            : "Guest mode"}
        </strong>
        <p>{message}</p>
      </div>

      <div className="auth-actions">
        <button type="button" className="secondary-button">
          Continue as guest
        </button>
        {sessionState === "signed_in" ? (
          <button type="button" className="primary-button" onClick={endGoogleSession}>
            Sign out
          </button>
        ) : (
          <button
            type="button"
            className="primary-button"
            disabled={sessionState === "signing_in" || sessionState === "config_needed"}
            onClick={startGoogleSession}
          >
            Sign in with Google
          </button>
        )}
      </div>

      {sessionState === "config_needed" ? (
        <small className="auth-note">Firebase config needed</small>
      ) : null}
    </section>
  );
}
