"use client";

import { onAuthStateChanged, type User } from "firebase/auth";
import { useEffect, useState } from "react";
import { verifyAuthSession, type AuthenticatedUser } from "../api";
import {
  ensureLocalAuthPersistence,
  getFirebaseAuth,
  signInWithGoogle,
  signOutOfGoogle,
} from "../firebaseClient";
import { isFirebaseConfigured } from "../firebaseConfig";

export type SessionState =
  | "config_needed"
  | "signed_out"
  | "signing_in"
  | "signed_in";

/**
 * Preserves AuthPanel's exact session logic: Firebase onAuthStateChanged ->
 * backend verifyAuthSession, plus sign in/out. UI-agnostic.
 */
export function useAuth() {
  const [sessionState, setSessionState] = useState<SessionState>(
    isFirebaseConfigured() ? "signed_out" : "config_needed",
  );
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [backendUser, setBackendUser] = useState<AuthenticatedUser | null>(null);

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
        return;
      }
      try {
        const idToken = await user.getIdToken();
        const session = await verifyAuthSession(idToken);
        setBackendUser(session.user);
        setSessionState("signed_in");
      } catch {
        setBackendUser(null);
        setSessionState("signed_out");
      }
    });
  }, []);

  async function signIn() {
    if (!isFirebaseConfigured()) {
      setSessionState("config_needed");
      return;
    }
    setSessionState("signing_in");
    try {
      await signInWithGoogle();
    } catch (error) {
      setSessionState("signed_out");
      throw error;
    }
  }

  async function signOut() {
    await signOutOfGoogle();
  }

  return {
    sessionState,
    firebaseUser,
    backendUser,
    isSignedIn: sessionState === "signed_in",
    displayName: backendUser?.display_name ?? firebaseUser?.displayName ?? null,
    email: backendUser?.email ?? firebaseUser?.email ?? null,
    signIn,
    signOut,
  };
}
