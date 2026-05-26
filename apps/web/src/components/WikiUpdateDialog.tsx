"use client";

import type { WikiPreviewResponse } from "../lib/api";

type Props = {
  preview: WikiPreviewResponse;
  isBusy: boolean;
  onConfirm: (forceOverwrite: boolean) => void;
  onCancel: () => void;
};

export function WikiUpdateDialog({
  preview,
  isBusy,
  onConfirm,
  onCancel,
}: Props) {
  const remoteLines = (preview.remote_markdown ?? "").split("\n");
  const proposedLines = preview.proposed_markdown.split("\n");

  return (
    <div className="wiki-update-dialog" role="dialog" aria-modal="true">
      <div className="wiki-update-dialog-panel">
        <p className="eyebrow">Wiki update approval</p>
        <h3>
          {preview.requires_confirmation
            ? "Remote wiki changed"
            : "Update project wiki"}
        </h3>
        <p>
          {preview.requires_confirmation
            ? "Review the current Drive content before overwriting it with the latest SADify wiki."
            : "SADify will write the latest saved SAD summary to Wiki/Wiki.md."}
        </p>

        {preview.requires_confirmation ? (
          <div className="wiki-diff-grid">
            <section>
              <h4>Current Drive wiki</h4>
              <pre>
                {remoteLines.map((line, index) => (
                  <span key={`remote-${index}`}>
                    {line || " "}
                    {"\n"}
                  </span>
                ))}
              </pre>
            </section>
            <section>
              <h4>Proposed SADify wiki</h4>
              <pre>
                {proposedLines.map((line, index) => (
                  <span key={`proposed-${index}`}>
                    {line || " "}
                    {"\n"}
                  </span>
                ))}
              </pre>
            </section>
          </div>
        ) : null}

        <div className="dialog-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={isBusy}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="primary-button"
            disabled={isBusy}
            onClick={() => onConfirm(preview.requires_confirmation)}
          >
            {preview.requires_confirmation ? "Overwrite wiki" : "Update wiki"}
          </button>
        </div>
      </div>
    </div>
  );
}
