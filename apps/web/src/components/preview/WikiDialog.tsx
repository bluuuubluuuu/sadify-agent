"use client";

import type { WikiFilePreview, WikiPreviewResponse } from "../../lib/api";
import { Button } from "../ui/Button";
import styles from "./WikiDialog.module.css";

function fileStatus(file: WikiFilePreview, preview: WikiPreviewResponse) {
  if (preview.first_time_write) {
    return { label: "new", cls: styles.bNew };
  }
  if (preview.changed_files.includes(file.name)) {
    return preview.requires_confirmation
      ? { label: "conflict", cls: styles.bConflict }
      : { label: "updated", cls: styles.bUpd };
  }
  return { label: "unchanged", cls: styles.bSame };
}

export function WikiDialog({
  preview,
  isBusy,
  onConfirm,
  onCancel,
}: {
  preview: WikiPreviewResponse;
  isBusy: boolean;
  onConfirm: (forceOverwrite: boolean) => void;
  onCancel: () => void;
}) {
  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Update wiki">
      <div className={styles.panel}>
        <p className={styles.eyebrow}>Wiki update</p>
        <h3 className={styles.title}>
          {preview.requires_confirmation ? "Remote wiki files changed" : "Update project wiki"}
        </h3>
        <p className={styles.desc}>
          {preview.requires_confirmation
            ? "Some Drive files changed since the last write. Existing files are backed up before overwrite."
            : "SADify writes the latest saved SAD knowledge notes into the Wiki folder (existing files are backed up first)."}
        </p>

        <div className={styles.list}>
          {preview.files.map((file) => {
            const status = fileStatus(file, preview);
            return (
              <div key={file.name}>
                <div className={styles.row}>
                  <span className={styles.name}>{file.relative_path}</span>
                  <span className={`${styles.badge} ${status.cls}`}>{status.label}</span>
                </div>
                {status.label === "conflict" ? (
                  <details className={styles.diff}>
                    <summary>View proposed content</summary>
                    <pre className={styles.pre}>{file.proposed_markdown}</pre>
                  </details>
                ) : null}
              </div>
            );
          })}
        </div>

        <div className={styles.actions}>
          <Button variant="ghost" disabled={isBusy} onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="primary" loading={isBusy} onClick={() => onConfirm(true)}>
            {preview.requires_confirmation ? "Back up & overwrite" : "Back up & update"}
          </Button>
        </div>
      </div>
    </div>
  );
}
