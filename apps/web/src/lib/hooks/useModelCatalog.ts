"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { listModels, type ModelCatalogResponse } from "../api";

const STORAGE_KEY = "sadify:selectedModel";
const EMPTY_CATALOG: ModelCatalogResponse = { default: "", models: [] };

function selectableModel(catalog: ModelCatalogResponse, candidate: string | null) {
  return candidate && catalog.models.some((model) => model.id === candidate)
    ? candidate
    : null;
}

function catalogDefault(catalog: ModelCatalogResponse) {
  return (
    selectableModel(catalog, catalog.default) ??
    catalog.models[0]?.id ??
    ""
  );
}

export function useModelCatalog() {
  const [catalog, setCatalog] = useState<ModelCatalogResponse>(EMPTY_CATALOG);
  const [selectedModel, setSelectedModelState] = useState("");
  const [message, setMessage] = useState("");
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void listModels()
      .then((nextCatalog) => {
        if (cancelled) {
          return;
        }
        const stored =
          typeof window !== "undefined"
            ? window.localStorage.getItem(STORAGE_KEY)
            : null;
        const next = selectableModel(nextCatalog, stored) ?? catalogDefault(nextCatalog);
        setCatalog(nextCatalog);
        setSelectedModelState(next);
        setIsLoaded(true);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(STORAGE_KEY, next);
        }
        setMessage("");
      })
      .catch(() => {
        if (!cancelled) {
          setIsLoaded(true);
          setMessage("Using the default Gemini model.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setSelectedModel = useCallback(
    (modelId: string) => {
      const next = selectableModel(catalog, modelId) ?? catalogDefault(catalog);
      if (!next) {
        return;
      }
      setSelectedModelState(next);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next);
      }
    },
    [catalog],
  );

  const selected = useMemo(
    () => catalog.models.find((model) => model.id === selectedModel) ?? catalog.models[0],
    [catalog.models, selectedModel],
  );

  return { catalog, selected, selectedModel, isLoaded, message, setSelectedModel };
}
