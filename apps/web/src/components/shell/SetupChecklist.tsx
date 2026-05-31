"use client";

import { Icon } from "../ui/Icon";
import styles from "./Sidebar.module.css";

export function SetupChecklist({
  isSignedIn,
  connected,
  repoName,
  onConnectDrive,
}: {
  isSignedIn: boolean;
  connected: boolean;
  repoName?: string;
  onConnectDrive: () => void;
}) {
  return (
    <>
      <div className={styles.setupRow}>
        {isSignedIn ? (
          <Icon name="checkCircle" size={18} color="#34d399" />
        ) : (
          <Icon name="circle" size={18} color="var(--c-warn)" />
        )}
        {isSignedIn ? "Signed in" : "Sign in to save"}
      </div>
      {connected ? (
        <div className={styles.driveRow}>
          <Icon name="cloudCheck" size={18} color="#34d399" />
          {repoName ?? "Drive connected"}
        </div>
      ) : (
        <button
          type="button"
          className={`${styles.setupRow} ${styles.pending}`}
          onClick={onConnectDrive}
        >
          <Icon name="circle" size={18} color="var(--c-warn)" />
          Connect Drive
          <span className={styles.setupNote}>to save</span>
        </button>
      )}
    </>
  );
}
