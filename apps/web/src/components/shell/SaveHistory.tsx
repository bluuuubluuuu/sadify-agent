"use client";

import type { SadSaveSummary } from "../../lib/api";
import { Icon } from "../ui/Icon";
import styles from "./Sidebar.module.css";

function formatSavedAt(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function SaveHistory({
  saves,
  message,
}: {
  saves: SadSaveSummary[];
  message: string;
}) {
  if (!saves.length) {
    return <p className={styles.histMsg}>{message}</p>;
  }
  return (
    <ul className={styles.histList}>
      {saves.map((save) => (
        <li key={`${save.preview_id}-${save.save_id}`} className={styles.histRow}>
          <Icon name="fileText" size={15} color="#fff" className={styles.histIcon} />
          <span className={styles.histId}>{save.save_id}</span>
          {save.doc_url ? (
            <a className={styles.histOpen} href={save.doc_url} target="_blank" rel="noreferrer">
              Open
            </a>
          ) : null}
          <span className={styles.histTime}>{formatSavedAt(save.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}
