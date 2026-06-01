"use client";

import type { SourceRecord } from "../../lib/api";
import { Icon } from "../ui/Icon";
import styles from "./chat.module.css";

export function AttachChips({
  sources,
  busy,
  onRemove,
  onAdd,
}: {
  sources: SourceRecord[];
  busy?: boolean;
  onRemove: (fileName: string) => void;
  onAdd: () => void;
}) {
  if (!sources.length) {
    return null;
  }
  return (
    <div className={styles.stage}>
      {sources.map((source) => (
        <div key={source.source_id} className={styles.fchip}>
          <span className={styles.ficon}>
            <Icon name="fileText" size={16} color="#fff" />
          </span>
          <span style={{ minWidth: 0 }}>
            <span className={styles.fname} style={{ display: "block" }}>
              {source.original_file_name}
            </span>
            <span className={styles.fmeta}>{source.source_id}</span>
          </span>
          <button
            type="button"
            className={styles.removeX}
            aria-label={`Remove ${source.original_file_name}`}
            disabled={busy}
            onClick={() => onRemove(source.original_file_name)}
          >
            ×
          </button>
        </div>
      ))}
      <button type="button" className={styles.addMore} disabled={busy} onClick={onAdd}>
        <Icon name="plus" size={14} color="var(--c-secondary)" />
        Add file
      </button>
    </div>
  );
}
