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
  onCreateGithubIssues,
}: {
  saves: SadSaveSummary[];
  message: string;
  onCreateGithubIssues?: (save: SadSaveSummary) => void;
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
            <a
              className={styles.histOpen}
              href={save.doc_url}
              target="_blank"
              rel="noreferrer"
              aria-label={`Open SAD doc ${save.save_id}`}
              title={`Open SAD doc ${save.save_id}`}
            >
              Open
            </a>
          ) : null}
          <span className={styles.histTime}>{formatSavedAt(save.created_at)}</span>
          {save.has_github_issue_set && onCreateGithubIssues ? (
            <button
              type="button"
              className={styles.histGithub}
              aria-label={`Create GitHub issues from ${save.save_id}`}
              onClick={() => onCreateGithubIssues(save)}
            >
              <Icon name="openExternal" size={13} />
              Create GitHub issues
            </button>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
