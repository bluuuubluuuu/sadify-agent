"use client";

import { useState } from "react";
import { uploadSources, type SourceUploadResponse } from "../api";

/**
 * Preserves SourceUploadPanel's upload contract. Files are conversation-level:
 * we keep the full File[] client-side and re-upload the whole set on add/remove
 * so analysis_context + source_references always match the visible chips (uses
 * only the existing /sources/upload endpoint).
 */
export function useSources(onChange?: (response: SourceUploadResponse | null) => void) {
  const [files, setFiles] = useState<File[]>([]);
  const [response, setResponse] = useState<SourceUploadResponse | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function uploadAll(nextFiles: File[]) {
    if (!nextFiles.length) {
      setResponse(null);
      onChange?.(null);
      setMessage("");
      return;
    }
    setIsBusy(true);
    setMessage("Reading source files...");
    try {
      const resp = await uploadSources(nextFiles);
      setResponse(resp);
      onChange?.(resp);
      setMessage(`${resp.sources.length} source file(s) ready for traceable analysis.`);
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "SADify could not read these source files.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function add(newFiles: File[]) {
    if (!newFiles.length) {
      return;
    }
    const next = [...files, ...newFiles];
    setFiles(next);
    await uploadAll(next);
  }

  async function remove(fileName: string) {
    const next = files.filter((file) => file.name !== fileName);
    setFiles(next);
    await uploadAll(next);
  }

  function reset() {
    setFiles([]);
    setResponse(null);
    onChange?.(null);
    setMessage("");
  }

  return {
    files,
    reset,
    sources: response?.sources ?? [],
    errors: response?.errors ?? [],
    analysisContext: response?.analysis_context ?? "",
    sourceReferences: response?.sources.map((source) => source.source_id) ?? [],
    isBusy,
    message,
    add,
    remove,
  };
}
