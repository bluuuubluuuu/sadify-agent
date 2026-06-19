"use client";

import { useState } from "react";
import { Button } from "../ui/Button";
import { Icon } from "../ui/Icon";
import styles from "./agent.module.css";

const REPO_PATTERN = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;

/**
 * Per-user GitHub connect. The user pastes a fine-grained PAT + their owner/repo,
 * following the same steps used locally. The token is held in memory only for the
 * session and sent once at approve; the repo is persisted on the project so the
 * sidebar can show a per-project GitHub link.
 */
export function ConnectGithubModal({
  initialRepo,
  busy,
  error,
  repoLocked = false,
  onSubmit,
  onClose,
}: {
  initialRepo?: string | null;
  busy?: boolean;
  error?: string;
  repoLocked?: boolean;
  onSubmit: (token: string, repo: string) => void;
  onClose: () => void;
}) {
  const [token, setToken] = useState("");
  const [repo, setRepo] = useState(initialRepo ?? "");
  const canSubmit = token.trim().length > 0 && REPO_PATTERN.test(repo.trim());

  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label="Connect GitHub"
    >
      <div className={styles.panel}>
        <div className={styles.head}>
          <p className={styles.eyebrow}>SADify agent</p>
          <button type="button" className={styles.close} aria-label="Close" onClick={onClose}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <h3 className={styles.title}>Connect GitHub</h3>
        <p className={styles.desc}>
          {repoLocked
            ? "This prepared issue set is locked to its original repository. Enter a GitHub token to continue."
            : "Paste a GitHub token and your repository. The agent uses it to create source-grounded issues from this SAD."}
        </p>

        <div className={styles.connectHelp}>
          How to get a token:
          <ol>
            <li>
              GitHub →{" "}
              <a
                className={styles.connectLink}
                href="https://github.com/settings/personal-access-tokens/new"
                target="_blank"
                rel="noreferrer"
              >
                fine-grained personal access token
              </a>
            </li>
            <li>Repository access → only select repositories → your repo</li>
            <li>Permissions → Repository → Issues: Read and write</li>
            <li>Generate, then paste it below</li>
          </ol>
        </div>

        <div className={styles.connectField}>
          <label className={styles.connectLabel} htmlFor="gh-repo">
            Repository (owner/name)
          </label>
          <input
            id="gh-repo"
            className={styles.connectInput}
            placeholder="octocat/hello-world"
            value={repo}
            onChange={(event) => setRepo(event.target.value)}
            disabled={repoLocked}
            spellCheck={false}
            autoComplete="off"
          />
        </div>
        <div className={styles.connectField}>
          <label className={styles.connectLabel} htmlFor="gh-token">
            GitHub token
          </label>
          <input
            id="gh-token"
            className={styles.connectInput}
            type="password"
            placeholder="github_pat_…"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            spellCheck={false}
            autoComplete="off"
          />
        </div>

        <p className={styles.connectNote}>
          <Icon name="info" size={13} color="var(--c-subtle)" />
          Stored only for this session, never saved. Revoke the token after the demo.
        </p>

        {error ? <div className={styles.error}>{error}</div> : null}

        <div className={styles.bar}>
          <Button
            variant="primary"
            disabled={!canSubmit}
            loading={busy}
            leftIcon={<Icon name="openExternal" size={16} color="#fff" />}
            onClick={() => onSubmit(token.trim(), repo.trim())}
          >
            {repoLocked ? "Continue to approval" : "Connect & prepare issues"}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
