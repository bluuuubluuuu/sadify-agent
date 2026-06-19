"use client";

import { Button } from "../ui/Button";
import styles from "./CreateProjectDialog.module.css";

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  busy,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className={styles.overlay} role="alertdialog" aria-modal="true" aria-label={title}>
      <div className={styles.panel}>
        <p className={styles.eyebrow}>Drive Trash</p>
        <h3 className={styles.title}>{title}</h3>
        <p className={styles.desc}>{message}</p>
        <div className={styles.actions}>
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" loading={busy} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
