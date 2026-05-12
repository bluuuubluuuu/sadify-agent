"use client";

import { getApp, getApps, initializeApp } from "firebase/app";
import {
  browserLocalPersistence,
  getAuth,
  GoogleAuthProvider,
  setPersistence,
  signInWithPopup,
  signOut,
  type Auth,
} from "firebase/auth";
import { firebaseConfig, isFirebaseConfigured } from "./firebaseConfig";

let persistenceReady: Promise<void> | null = null;

export function getFirebaseAuth(): Auth {
  if (!isFirebaseConfigured()) {
    throw new Error("Firebase config needed");
  }

  const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
  return getAuth(app);
}

export function ensureLocalAuthPersistence(auth: Auth) {
  persistenceReady ??= setPersistence(auth, browserLocalPersistence);
  return persistenceReady;
}

export async function signInWithGoogle() {
  const auth = getFirebaseAuth();
  await ensureLocalAuthPersistence(auth);
  const provider = new GoogleAuthProvider();
  const result = await signInWithPopup(auth, provider);
  return result.user;
}

export async function signOutOfGoogle() {
  const auth = getFirebaseAuth();
  await signOut(auth);
}
