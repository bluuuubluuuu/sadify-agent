"use client";

import { useState } from "react";
import type { DriveRepoRecord } from "../../lib/api";
import { Icon } from "../ui/Icon";
import styles from "./Sidebar.module.css";

export function AccountMenu({
  name,
  email,
  repo,
  onConnect,
  onDisconnect,
  onSignIn,
  onSignOut,
}: {
  name: string | null;
  email: string | null;
  repo: DriveRepoRecord | null;
  onConnect: () => void;
  onDisconnect: () => void;
  onSignIn: () => void;
  onSignOut: () => void;
}) {
  const [open, setOpen] = useState(false);
  const isSignedIn = Boolean(name || email);
  const initials = isSignedIn ? (name ?? email ?? "?").slice(0, 2).toUpperCase() : "?";
  const connected = Boolean(repo && !repo.saves_blocked);

  return (
    <div className={styles.acctWrap}>
      {open ? (
        <button
          type="button"
          className={styles.scrim}
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <button
        type="button"
        className={styles.acctRow}
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className={styles.avatar}>{initials}</span>
        <span style={{ minWidth: 0, flex: 1 }}>
          <span className={styles.acctName} style={{ display: "block" }}>
            {isSignedIn ? (name ?? email ?? "Account") : "Guest"}
          </span>
          {isSignedIn && email ? (
            <span className={styles.acctEmail} style={{ display: "block" }}>
              {email}
            </span>
          ) : null}
        </span>
        {isSignedIn ? (
          <span className={`${styles.acctChip} ${connected ? styles.acctChipOn : styles.acctChipOff}`}>
            <Icon
              name={connected ? "cloudCheck" : "circle"}
              size={12}
              color={connected ? "#a7f3d0" : "#fde68a"}
            />
            {connected ? "Drive" : "Connect"}
          </span>
        ) : (
          <span className={`${styles.acctChip} ${styles.acctChipOff}`}>Sign in</span>
        )}
      </button>

      {open ? (
        <div className={styles.menu} role="menu">
          {isSignedIn ? (
            <>
              <div className={styles.menuHead}>Google Drive</div>
              {connected && repo ? (
                <>
                  <div className={styles.mRow}>
                    <Icon name="cloudCheck" size={18} color="var(--c-subtle)" />
                    {repo.repo_folder_name}
                    <span className={styles.mMeta}>Connected</span>
                  </div>
                  {repo.repo_url ? (
                    <a
                      className={styles.mRow}
                      href={repo.repo_url}
                      target="_blank"
                      rel="noreferrer"
                      role="menuitem"
                    >
                      <Icon name="openExternal" size={18} color="var(--c-subtle)" />
                      Open repo in Drive
                    </a>
                  ) : null}
                  <button
                    type="button"
                    className={`${styles.mRow} ${styles.mDanger}`}
                    role="menuitem"
                    onClick={() => {
                      setOpen(false);
                      onDisconnect();
                    }}
                  >
                    <Icon name="cloudCheck" size={18} color="var(--c-danger)" />
                    Disconnect Drive
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className={styles.mRow}
                  role="menuitem"
                  onClick={() => {
                    setOpen(false);
                    onConnect();
                  }}
                >
                  <Icon name="cloudCheck" size={18} color="var(--c-subtle)" />
                  Connect Google Drive
                </button>
              )}
              <div className={styles.sep} />
              <button
                type="button"
                className={`${styles.mRow} ${styles.mDanger}`}
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  onSignOut();
                }}
              >
                <Icon name="signOut" size={18} color="var(--c-danger)" />
                Sign out
              </button>
            </>
          ) : (
            <button
              type="button"
              className={styles.mRow}
              role="menuitem"
              onClick={() => {
                setOpen(false);
                onSignIn();
              }}
            >
              <Icon name="google" size={18} color="var(--c-primary)" />
              Sign in with Google
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}
