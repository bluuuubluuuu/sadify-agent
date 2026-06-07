"use client";

import type {
  AgentEvent,
  AgentFinalizeStatus,
  AgentGithubIssue,
  AgentProposedAction,
} from "../../lib/api";
import { Button } from "../ui/Button";
import { Icon, type IconName } from "../ui/Icon";
import styles from "./agent.module.css";

const TOOL_ICON: Record<string, IconName> = {
  get_readiness: "checkCircle",
  ask_clarification: "question",
  generate_sad: "fileText",
  review_sad: "info",
  extract_dev_tasks: "checkCircle",
  create_github_issues: "openExternal",
  save_to_drive: "uploadCloud",
  update_wiki: "book",
};

const ACTION_META: Record<string, { icon: IconName; what: string }> = {
  save_to_drive: {
    icon: "fileText",
    what: "The SAD document → saved into your project repo folder in Drive",
  },
  update_wiki: {
    icon: "book",
    what: "Structured knowledge notes → written to the project wiki folder",
  },
  overwrite_wiki: {
    icon: "book",
    what: "Overwrite the changed wiki files in the project wiki folder",
  },
};

type CompletedAction = {
  tool?: string;
  status?: string;
  doc_path?: string;
  doc_url?: string;
  file_count?: number;
};

type CompletedGithubIssue = {
  number?: string | number;
  url?: string;
  title?: string;
};

type AgentResult = {
  approval_id?: string;
  preview_id?: string;
  repo?: string;
  proposed_actions?: AgentProposedAction[];
  question?: string;
  why?: string;
  missing_basics?: string[];
  actions?: Array<Record<string, unknown>>;
  completed_actions?: Array<Record<string, unknown>>;
  issues?: CompletedGithubIssue[];
};

export function AgentTimeline({
  mode = "finalize",
  events,
  status,
  result,
  isStreaming,
  isApproving,
  error,
  onApprove,
  onPrepareGithubIssues,
  isGithubPreparing = false,
  githubSetupNotice = "",
  onContinueInChat,
  onClose,
}: {
  mode?: "finalize" | "github";
  events: AgentEvent[];
  status: AgentFinalizeStatus | null;
  result: AgentResult | null;
  isStreaming: boolean;
  isApproving: boolean;
  error: string;
  onApprove: () => void;
  onPrepareGithubIssues?: (previewId: string) => void;
  isGithubPreparing?: boolean;
  githubSetupNotice?: string;
  onContinueInChat: () => void;
  onClose: () => void;
}) {
  const isGithubMode = mode === "github";
  const githubAction = result?.proposed_actions?.find(
    (action) => action.id === "create_github_issues",
  );
  const githubIssues = githubAction?.issues ?? [];
  const repo = githubAction?.repo ?? result?.repo ?? "configured repo";
  const issueCount = githubAction?.issue_count ?? githubIssues.length;
  const agentSavedPreviewId = _savedPreviewId(result);

  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label={
        isGithubMode
          ? "Create GitHub issues with the SADify agent"
          : "Finalize with the SADify agent"
      }
    >
      <div className={styles.panel}>
        <div className={styles.head}>
          <p className={styles.eyebrow}>SADify agent</p>
          <button type="button" className={styles.close} aria-label="Close" onClick={onClose}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <h3 className={styles.title}>
          {isGithubMode ? "Preparing GitHub issues" : "Finalizing your SAD"}
        </h3>
        <p className={styles.desc}>
          {isGithubMode
            ? "The agent extracts source-grounded developer tasks, calls GitHub through MCP, then pauses for your approval before creating issues."
            : "The agent checks readiness, drafts the SAD, reviews its own draft, then pauses for your approval before saving anything."}
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

        {isGithubMode && status === "awaiting_approval" && result?.approval_id ? (
          <div className={`${styles.approval} ${styles.githubApproval}`}>
            <p className={styles.approvalTitle}>
              <Icon name="openExternal" size={14} color="var(--c-secondary)" />
              Create {issueCount} GitHub issues in {repo}
            </p>
            <div className={styles.githubRepo}>{repo}</div>
            <ul className={styles.githubIssueList}>
              {githubIssues.map((issue: AgentGithubIssue, index) => (
                <li key={`${issue.title}-${index}`}>
                  <strong>{issue.title}</strong>
                  {issue.labels?.length ? <small>{issue.labels.join(", ")}</small> : null}
                </li>
              ))}
            </ul>
            <div className={styles.bar}>
              <Button
                variant="primary"
                loading={isApproving}
                leftIcon={<Icon name="openExternal" size={16} color="#fff" />}
                onClick={onApprove}
              >
                Approve &amp; create issues
              </Button>
              <Button variant="ghost" onClick={onClose}>
                Not now
              </Button>
            </div>
          </div>
        ) : null}

        {!isGithubMode && status === "awaiting_approval" && result?.approval_id ? (
          <div className={styles.approval}>
            {result.completed_actions && result.completed_actions.length ? (
              <p className={styles.savedNote}>
                <Icon name="checkCircle" size={14} color="var(--c-success)" />
                SAD document already saved to your repo — the wiki has changed
                files, confirm overwrite to update it, or skip with “Not now”.
              </p>
            ) : null}
            <p className={styles.approvalTitle}>
              <Icon name="info" size={14} color="var(--c-secondary)" />
              {result.completed_actions && result.completed_actions.length
                ? "Update the project wiki?"
                : "The draft is ready — approve to save"}
            </p>
            <ul className={styles.actions}>
              {(result.proposed_actions ?? []).map((action) => {
                const meta = ACTION_META[action.id];
                return (
                  <li key={action.id} className={styles.actionItem}>
                    <Icon
                      name={meta?.icon ?? "uploadCloud"}
                      size={16}
                      color="var(--c-secondary)"
                    />
                    <span className={styles.actionText}>
                      <strong>{action.label}</strong>
                      {meta ? <small>{meta.what}</small> : null}
                    </span>
                  </li>
                );
              })}
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

        {!isGithubMode && status === "asked_clarification" ? (
          <div className={styles.clarify}>
            <p className={styles.clarifyTitle}>
              I need one basic before I can draft a solid SAD
            </p>
            {result?.question ? (
              <p className={styles.clarifyQ}>{result.question}</p>
            ) : result?.missing_basics && result.missing_basics.length ? (
              <ul className={styles.clarifyList}>
                {result.missing_basics.map((basic) => (
                  <li key={basic}>{basic}</li>
                ))}
              </ul>
            ) : (
              <p className={styles.clarifyQ}>
                A little more detail is needed before I can finalize.
              </p>
            )}
            {result?.why ? <p className={styles.clarifyHint}>{result.why}</p> : null}
            <div className={styles.bar}>
              <Button
                variant="primary"
                leftIcon={<Icon name="arrowRight" size={16} color="#fff" />}
                onClick={onContinueInChat}
              >
                Continue in chat
              </Button>
              <Button variant="ghost" onClick={onClose}>
                Not now
              </Button>
            </div>
          </div>
        ) : null}

        {isGithubMode && status === "completed" ? (
          <div className={`${styles.doneBlock} ${styles.githubDone}`}>
            <p className={styles.doneTitle}>
              <Icon name="checkCircle" size={18} color="var(--c-success)" />
              GitHub issues created
            </p>
            <ul className={styles.actions}>
              {(result?.issues ?? []).map((issue, index) => (
                <li key={index} className={styles.actionItem}>
                  <Icon name="openExternal" size={16} color="var(--c-success)" />
                  <span className={styles.actionText}>
                    <strong>
                      {issue.number ? `Issue #${issue.number}` : "GitHub issue"}
                    </strong>
                    {issue.title ? <small>{issue.title}</small> : null}
                    {issue.url ? (
                      <a href={issue.url} target="_blank" rel="noreferrer">
                        Open issue
                      </a>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {!isGithubMode && status === "completed" ? (
          <div className={styles.doneBlock}>
            <p className={styles.doneTitle}>
              <Icon name="checkCircle" size={18} color="var(--c-success)" />
              Saved to your Drive
            </p>
            <ul className={styles.actions}>
              {((result?.actions ?? []) as CompletedAction[]).map((action, index) => {
                const tool = String(action.tool ?? "");
                if (tool === "save_to_drive") {
                  return (
                    <li key={index} className={styles.actionItem}>
                      <Icon name="fileText" size={16} color="var(--c-success)" />
                      <span className={styles.actionText}>
                        <strong>SAD document saved to repo</strong>
                        {action.doc_path ? <small>{action.doc_path}</small> : null}
                        {action.doc_url ? (
                          <a href={action.doc_url} target="_blank" rel="noreferrer">
                            Open in Drive
                          </a>
                        ) : null}
                      </span>
                    </li>
                  );
                }
                return (
                  <li key={index} className={styles.actionItem}>
                    <Icon name="book" size={16} color="var(--c-success)" />
                    <span className={styles.actionText}>
                      <strong>Project wiki updated</strong>
                      <small>
                        {action.file_count ?? 0} file
                        {action.file_count === 1 ? "" : "s"} written to the wiki folder
                      </small>
                    </span>
                  </li>
                );
              })}
            </ul>
            {agentSavedPreviewId && onPrepareGithubIssues ? (
              <>
                {githubSetupNotice ? (
                  <div className={styles.githubSetup}>{githubSetupNotice}</div>
                ) : null}
                <div className={styles.bar}>
                  <Button
                    variant="secondary"
                    loading={isGithubPreparing}
                    disabled={Boolean(githubSetupNotice)}
                    leftIcon={<Icon name="openExternal" size={16} />}
                    onClick={() => onPrepareGithubIssues(agentSavedPreviewId)}
                  >
                    Prepare GitHub issues
                  </Button>
                </div>
              </>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function _savedPreviewId(result: AgentResult | null): string | null {
  const direct = result?.preview_id;
  if (direct) {
    return direct;
  }
  const actions = result?.actions ?? result?.completed_actions ?? [];
  for (const action of actions) {
    if (action.tool === "save_to_drive" && typeof action.preview_id === "string") {
      return action.preview_id;
    }
  }
  return null;
}
