"use client";

import { useState } from "react";
import {
  uploadSources,
  type SourceRecord,
  type SourceUploadResponse,
} from "../lib/api";

type Props = {
  onSourcesUploaded: (response: SourceUploadResponse) => void;
};

export function SourceUploadPanel({ onSourcesUploaded }: Props) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [sourceUpload, setSourceUpload] = useState<SourceUploadResponse | null>(null);
  const [message, setMessage] = useState("Upload business sources before analysis.");
  const [isBusy, setIsBusy] = useState(false);

  async function uploadSelectedSources() {
    if (selectedFiles.length === 0) {
      setMessage("Choose at least one MD, TXT, PDF, DOCX, XLSX, or CSV file.");
      return;
    }

    setIsBusy(true);
    setMessage("Reading source files...");
    try {
      const response = await uploadSources(selectedFiles);
      setSourceUpload(response);
      onSourcesUploaded(response);
      setMessage(
        `${response.sources.length} source file(s) ready for traceable analysis.`,
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "SADify could not upload these source files.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="source-panel" aria-label="Source upload traceability">
      <div className="source-copy">
        <p className="eyebrow">Sources</p>
        <h2>Upload source files</h2>
        <p>{message}</p>
      </div>

      <label className="source-input">
        <span>Business files</span>
        <input
          type="file"
          multiple
          accept=".md,.markdown,.txt,.pdf,.docx,.xlsx,.csv"
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            setSelectedFiles(files);
            setMessage(
              files.length
                ? `${files.length} file(s) selected.`
                : "Upload business sources before analysis.",
            );
          }}
        />
      </label>

      <button
        type="button"
        className="secondary-button"
        disabled={isBusy}
        onClick={uploadSelectedSources}
      >
        Upload files
      </button>

      {sourceUpload ? (
        <div className="source-result">
          <details className="source-traceability" open>
            <summary>Source traceability</summary>
            <div className="source-list">
              {sourceUpload.sources.map((source) => (
                <SourceSummary key={source.source_id} source={source} />
              ))}
            </div>
          </details>

          {sourceUpload.errors.length > 0 ? (
            <details className="source-errors" open>
              <summary>Unsupported files</summary>
              <ul>
                {sourceUpload.errors.map((error) => (
                  <li key={error.filename}>
                    <strong>{error.filename}</strong>: {error.message}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function SourceSummary({ source }: { source: SourceRecord }) {
  return (
    <article className="source-card">
      <div>
        <strong>{source.source_id}</strong>
        <span>{source.original_file_name}</span>
      </div>
      <p>{source.extracted_text_preview}</p>
      <small>
        {source.extraction_summary} Trace unit:{" "}
        {source.traceability_units[0]?.unit_type ?? "file"}
      </small>
    </article>
  );
}
