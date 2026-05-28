"use client";

import { useEffect, useState } from "react";

type Props = {
  suggestedName: string;
  isBusy: boolean;
  onSubmit: (name: string) => void;
  onCancel: () => void;
};

export function CreateProjectDialog({
  suggestedName,
  isBusy,
  onSubmit,
  onCancel,
}: Props) {
  const [name, setName] = useState(suggestedName);

  useEffect(() => {
    setName(suggestedName);
  }, [suggestedName]);

  return (
    <div className="wiki-update-dialog" role="dialog" aria-modal="true">
      <div className="wiki-update-dialog-panel">
        <p className="eyebrow">Project folder</p>
        <h3>Create project</h3>
        <p>Name the Drive project folder SADify should save this work into.</p>

        <label className="drive-input">
          <span>Project name</span>
          <input
            value={name}
            disabled={isBusy}
            onChange={(event) => setName(event.target.value)}
          />
        </label>

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
            disabled={isBusy || !name.trim()}
            onClick={() => onSubmit(name)}
          >
            Create project
          </button>
        </div>
      </div>
    </div>
  );
}
