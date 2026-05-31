"use client";

import { Icon } from "../ui/Icon";
import { Button } from "../ui/Button";
import styles from "./Sidebar.module.css";

export function ConnectDriveBanner({ onConnect }: { onConnect: () => void }) {
  return (
    <div className={styles.banner}>
      <span className={styles.bannerText}>
        <Icon name="cloudCheck" size={18} color="var(--c-warn-fg)" />
        Connect Google Drive to save your SAD &amp; wiki
      </span>
      <Button variant="primary" onClick={onConnect}>
        Connect
      </Button>
    </div>
  );
}
