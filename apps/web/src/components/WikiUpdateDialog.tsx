"use client";

import type { WikiFilePreview, WikiPreviewResponse } from "../lib/api";

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
  const changedFiles = preview.files.filter((file) =>
    preview.changed_files.includes(file.name),
  );

  return (
    <div className="wiki-update-dialog" role="dialog" aria-modal="true">
      <div className="wiki-update-dialog-panel">
        <p className="eyebrow">Wiki update approval</p>
        <h3>
          {preview.requires_confirmation
            ? "Remote wiki files changed"
            : "Update project wiki"}
        </h3>
        <p>
          {preview.requires_confirmation
            ? "Review the changed Drive files before overwriting them with the latest SADify wiki."
            : "SADify will write the latest saved SAD knowledge notes into the Wiki folder."}
        </p>

        {preview.requires_confirmation ? (
          <div className="wiki-diff-grid">
            {changedFiles.map((file) => (
              <FileDiff key={file.name} file={file} />
            ))}
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
            onClick={() => onConfirm(true)}
          >
            {preview.requires_confirmation ? "Overwrite all" : "Update wiki"}
          </button>
        </div>
      </div>
    </div>
  );
}

function FileDiff({ file }: { file: WikiFilePreview }) {
  const remoteLines = (file.remote_markdown ?? "").split("\n");
  const proposedLines = file.proposed_markdown.split("\n");

  return (
    <article>
      <h4>{file.relative_path}</h4>
      <section>
        <h5>Current Drive file</h5>
        <pre>
          {remoteLines.map((line, index) => (
            <span key={`remote-${file.name}-${index}`}>
              {line || " "}
              {"\n"}
            </span>
          ))}
        </pre>
      </section>
      <section>
        <h5>Proposed SADify file</h5>
        <pre>
          {proposedLines.map((line, index) => (
            <span key={`proposed-${file.name}-${index}`}>
              {line || " "}
              {"\n"}
            </span>
          ))}
        </pre>
      </section>
    </article>
  );
}
