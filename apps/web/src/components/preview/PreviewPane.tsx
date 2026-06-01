"use client";

import type { SadPreviewResponse, SadSaveRecord } from "../../lib/api";
import { Icon } from "../ui/Icon";
import { Button } from "../ui/Button";
import styles from "./PreviewPane.module.css";

const READINESS_LABEL: Record<string, string> = {
  ready: "Ready",
  needs_input: "Needs input",
  risk: "Risk",
};

export function PreviewPane({
  preview,
  record,
  isDraftReady,
  canUpdateWiki,
  isSaving,
  isWikiBusy,
  saveMessage,
  wikiMessage,
  onSave,
  onUpdateWiki,
  onRefine,
}: {
  preview: SadPreviewResponse;
  record: SadSaveRecord | null;
  isDraftReady: boolean;
  canUpdateWiki: boolean;
  isSaving: boolean;
  isWikiBusy: boolean;
  saveMessage: string;
  wikiMessage: string;
  onSave: () => void;
  onUpdateWiki: () => void;
  onRefine: () => void;
}) {
  return (
    <div className={styles.pane}>
      <div className={styles.head}>
        <div className={styles.title}>
          <Icon name="fileText" size={20} color="var(--c-secondary)" />
          {preview.title}
        </div>
        <div className={styles.pills}>
          <span className={`${styles.pill} ${styles.ready}`}>
            <Icon name="checkCircle" size={13} color="var(--c-success)" />
            {isDraftReady ? "Draft-ready" : `${preview.it_readiness.score}%`}
          </span>
          {!record ? (
            <span className={`${styles.pill} ${styles.temp}`}>
              <Icon name="info" size={13} color="var(--c-warn-fg)" />
              Temporary — not saved yet
            </span>
          ) : null}
        </div>
      </div>

      <div className={styles.doc}>
        {record ? (
          <div className={styles.success}>
            <Icon name="checkCircle" size={18} color="var(--c-success)" />
            <span>
              <b>Saved to project repo</b>
              <span>
                {record.save_id} · {record.sad_doc.path}
              </span>
            </span>
            {record.sad_doc.url ? (
              <a
                className={styles.openDoc}
                href={record.sad_doc.url}
                target="_blank"
                rel="noreferrer"
              >
                <Icon name="openExternal" size={13} color="var(--c-primary)" />
                Open in Drive
              </a>
            ) : null}
          </div>
        ) : null}

        {preview.sections.map((section) => (
          <div key={section.title} className={styles.section}>
            <h4>{section.title}</h4>
            <p>{section.body}</p>
            {section.source_references.length ? (
              <div className={styles.sref}>Sources: {section.source_references.join(", ")}</div>
            ) : null}
          </div>
        ))}

        {preview.assumptions.length ? (
          <div className={`${styles.block} ${styles.assum}`}>
            <b>
              <Icon name="info" size={14} color="var(--c-primary)" />
              Assumptions we made
            </b>
            <ul>
              {preview.assumptions.map((assumption) => (
                <li key={assumption}>{assumption}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {preview.open_questions.length ? (
          <div className={`${styles.block} ${styles.openq}`}>
            <b>
              <Icon name="question" size={14} color="var(--c-secondary)" />
              Questions to confirm with the business
            </b>
            <ul>
              {preview.open_questions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <details className={styles.checklist}>
          <summary>Review readiness checklist</summary>
          <div className={styles.check}>
            {preview.it_readiness.checklist.map((item) => (
              <article key={item.id}>
                <strong>{item.label}</strong>
                <small>{READINESS_LABEL[item.status] ?? item.status}</small>
                <p>{item.reason}</p>
              </article>
            ))}
          </div>
        </details>
      </div>

      {saveMessage || wikiMessage ? (
        <div className={styles.note}>{saveMessage || wikiMessage}</div>
      ) : null}

      <div className={styles.bar}>
        <Button
          variant="primary"
          loading={isSaving}
          disabled={Boolean(record)}
          leftIcon={<Icon name="uploadCloud" size={16} color="#fff" />}
          onClick={onSave}
        >
          {record ? "Saved" : "Save to Drive"}
        </Button>
        {canUpdateWiki ? (
          <Button
            variant="secondary"
            loading={isWikiBusy}
            leftIcon={<Icon name="book" size={16} />}
            onClick={onUpdateWiki}
          >
            Update wiki
          </Button>
        ) : null}
        <Button
          variant="ghost"
          className={styles.refine}
          leftIcon={<Icon name="edit" size={16} />}
          onClick={onRefine}
        >
          Refine in chat
        </Button>
      </div>
    </div>
  );
}
