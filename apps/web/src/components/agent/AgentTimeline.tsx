"use client";

import type { AgentEvent, AgentFinalizeStatus, AgentProposedAction } from "../../lib/api";
import { Button } from "../ui/Button";
import { Icon, type IconName } from "../ui/Icon";
import styles from "./agent.module.css";

const TOOL_ICON: Record<string, IconName> = {
  get_readiness: "checkCircle",
  ask_clarification: "question",
  generate_sad: "fileText",
  review_sad: "info",
  save_to_drive: "uploadCloud",
  update_wiki: "book",
};

type AgentResult = {
  approval_id?: string;
  preview_id?: string;
  proposed_actions?: AgentProposedAction[];
  question?: string;
  actions?: Array<Record<string, unknown>>;
};

export function AgentTimeline({
  events,
  status,
  result,
  isStreaming,
  isApproving,
  error,
  onApprove,
  onClose,
}: {
  events: AgentEvent[];
  status: AgentFinalizeStatus | null;
  result: AgentResult | null;
  isStreaming: boolean;
  isApproving: boolean;
  error: string;
  onApprove: () => void;
  onClose: () => void;
}) {
  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label="Finalize with the SADify agent"
    >
      <div className={styles.panel}>
        <div className={styles.head}>
          <p className={styles.eyebrow}>SADify agent</p>
          <button type="button" className={styles.close} aria-label="Close" onClick={onClose}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <h3 className={styles.title}>Finalizing your SAD</h3>
        <p className={styles.desc}>
          The agent checks readiness, drafts the SAD, reviews its own draft, then pauses
          for your approval before saving anything.
        </p>

        <ol className={styles.timeline}>
          {events.map((event, index) => (
            <li key={index} className={styles.step}>
              <span className={styles.dot}>
                <Icon name={TOOL_ICON[event.tool ?? ""] ?? "sparkle"} size={14} color="var(--c-primary)" />
              </span>
              <div className={styles.stepBody}>
                {event.reasoning ? <p className={styles.reasoning}>{event.reasoning}</p> : null}
                <p className={styles.summary}>{event.summary}</p>
              </div>
            </li>
          ))}
          {isStreaming ? (
            <li className={`${styles.step} ${styles.streaming}`}>
              <span className={styles.dot}>
                <Icon name="sparkle" size={14} color="var(--c-secondary)" />
              </span>
              <div className={styles.stepBody}>
                <p className={styles.summary}>Thinking…</p>
              </div>
            </li>
          ) : null}
        </ol>

        {error ? <div className={styles.error}>{error}</div> : null}

        {status === "awaiting_approval" && result?.approval_id ? (
          <div className={styles.approval}>
            <p className={styles.approvalTitle}>
              <Icon name="info" size={14} color="var(--c-secondary)" />
              The draft is ready — approve to save
            </p>
            <ul className={styles.actions}>
              {(result.proposed_actions ?? []).map((action) => (
                <li key={action.id}>{action.label}</li>
              ))}
            </ul>
            <div className={styles.bar}>
              <Button
                variant="primary"
                loading={isApproving}
                leftIcon={<Icon name="uploadCloud" size={16} color="#fff" />}
                onClick={onApprove}
              >
                Approve &amp; save
              </Button>
              <Button variant="ghost" onClick={onClose}>
                Not now
              </Button>
            </div>
          </div>
        ) : null}

        {status === "asked_clarification" ? (
          <div className={styles.clarify}>
            <p className={styles.clarifyTitle}>The agent needs one more answer</p>
            {result?.question ? <p className={styles.clarifyQ}>{result.question}</p> : null}
            <p className={styles.clarifyHint}>
              Answer it back in the chat, then finalize again.
            </p>
          </div>
        ) : null}

        {status === "completed" ? (
          <div className={styles.done}>
            <Icon name="checkCircle" size={18} color="var(--c-success)" />
            <span>Saved. The approved actions ran successfully.</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
