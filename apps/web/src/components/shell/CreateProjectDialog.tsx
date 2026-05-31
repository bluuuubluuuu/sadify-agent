"use client";

import { useEffect, useState } from "react";
import { Button } from "../ui/Button";
import styles from "./CreateProjectDialog.module.css";

export function CreateProjectDialog({
  suggestedName,
  isBusy,
  onSubmit,
  onCancel,
}: {
  suggestedName: string;
  isBusy: boolean;
  onSubmit: (name: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(suggestedName);

  useEffect(() => {
    setName(suggestedName);
  }, [suggestedName]);

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Create project">
      <div className={styles.panel}>
        <p className={styles.eyebrow}>Project folder</p>
        <h3 className={styles.title}>Create project</h3>
        <p className={styles.desc}>
          Name the Drive project folder SADify should save this work into.
        </p>
        <label className={styles.field}>
          Project name
          <input
            className={styles.input}
            value={name}
            disabled={isBusy}
            autoFocus
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <div className={styles.actions}>
          <Button variant="ghost" onClick={onCancel} disabled={isBusy}>
            Cancel
          </Button>
          <Button variant="primary" loading={isBusy} disabled={!name.trim()} onClick={() => onSubmit(name)}>
            Create project
          </Button>
        </div>
      </div>
    </div>
  );
}
