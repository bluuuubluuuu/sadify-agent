"use client";

import type { ModelCatalogResponse } from "../../lib/api";
import styles from "./chat.module.css";

export function ModelPicker({
  catalog,
  selectedModel,
  onChange,
}: {
  catalog: ModelCatalogResponse;
  selectedModel: string;
  onChange: (modelId: string) => void;
}) {
  const selected = catalog.models.find((model) => model.id === selectedModel);

  return (
    <label className={styles.modelPicker}>
      <span className={styles.modelLabel}>Gemini</span>
      <select
        aria-label="Gemini model"
        className={styles.modelSelect}
        disabled={catalog.models.length === 0}
        value={selectedModel}
        onChange={(event) => onChange(event.target.value)}
      >
        {catalog.models.length === 0 ? (
          <option value="">Loading models...</option>
        ) : (
          catalog.models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.label}
              {model.hint ? ` - ${model.hint}` : ""}
            </option>
          ))
        )}
      </select>
      {selected?.hint ? <span className={styles.modelHint}>{selected.hint}</span> : null}
    </label>
  );
}
