"use client";

import { useState } from "react";
import type { DriveRepoRecord } from "../../lib/api";
import { Icon } from "../ui/Icon";
import styles from "./Sidebar.module.css";

export function AccountMenu({
  name,
  email,
  repo,
  onDisconnect,
  onSignOut,
}: {
  name: string | null;
  email: string | null;
  repo: DriveRepoRecord | null;
  onDisconnect: () => void;
  onSignOut: () => void;
}) {
  const [open, setOpen] = useState(false);
  const initials = (name ?? email ?? "?").slice(0, 2).toUpperCase();
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
        <span style={{ minWidth: 0 }}>
          <span className={styles.acctName} style={{ display: "block" }}>
            {name ?? "Guest"}
          </span>
          {email ? (
            <span className={styles.acctEmail} style={{ display: "block" }}>
              {email}
            </span>
          ) : null}
        </span>
      </button>

      {open ? (
        <div className={styles.menu} role="menu">
          <div className={styles.menuHead}>Signed in</div>
          <div className={styles.mRow}>
            <Icon name="user" size={18} color="var(--c-subtle)" />
            {name ?? email ?? "Account"}
          </div>
          <div className={styles.sep} />
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
            <div className={styles.mRow}>
              <Icon name="circle" size={18} color="var(--c-subtle)" />
              Not connected
            </div>
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
        </div>
      ) : null}
    </div>
  );
}
