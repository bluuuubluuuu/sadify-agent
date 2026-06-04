"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type { ModelCatalogResponse } from "../../lib/api";
import { Icon } from "../ui/Icon";
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
  const [open, setOpen] = useState(false);
  const [dropUp, setDropUp] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const selected = catalog.models.find((model) => model.id === selectedModel);
  const disabled = catalog.models.length === 0;

  function toggle() {
    setOpen((value) => {
      const next = !value;
      if (next && buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        // Open upward only when there isn't room below (e.g. the pill sits
        // just above the composer); otherwise drop down so the menu is never
        // clipped at the top of the viewport.
        setDropUp(window.innerHeight - rect.bottom < 240);
      }
      return next;
    });
  }

  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function close(focusButton: boolean) {
    setOpen(false);
    if (focusButton) {
      buttonRef.current?.focus();
    }
  }

  function choose(modelId: string) {
    onChange(modelId);
    close(true);
  }

  function onMenuKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLLIElement>("[role='option']"),
    );
    const current = items.indexOf(document.activeElement as HTMLLIElement);
    if (event.key === "Escape") {
      event.preventDefault();
      close(true);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      items[Math.min(current + 1, items.length - 1)]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      items[Math.max(current - 1, 0)]?.focus();
    }
  }

  return (
    <div className={styles.modelRoot} ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className={styles.modelPill}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Gemini model"
        disabled={disabled}
        onClick={toggle}
      >
        <Icon name="sparkle" size={14} color="var(--c-secondary)" />
        <span className={styles.modelPillName}>
          {selected?.label ?? "Loading models..."}
        </span>
        <Icon name="caretDown" size={12} color="var(--c-subtle)" />
      </button>
      {open ? (
        <ul
          className={`${styles.modelMenu} ${dropUp ? styles.modelMenuUp : ""}`}
          role="listbox"
          aria-label="Gemini model"
          onKeyDown={onMenuKeyDown}
        >
          {catalog.models.map((model) => {
            const active = model.id === selectedModel;
            return (
              <li
                key={model.id}
                role="option"
                aria-selected={active}
                tabIndex={0}
                ref={active ? (element) => element?.focus() : undefined}
                className={`${styles.modelItem} ${active ? styles.modelItemOn : ""}`}
                onClick={() => choose(model.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    choose(model.id);
                  }
                }}
              >
                <span className={styles.modelItemText}>
                  <span className={styles.modelItemName}>{model.label}</span>
                  {model.hint ? (
                    <span className={styles.modelItemHint}>{model.hint}</span>
                  ) : null}
                </span>
                {active ? (
                  <Icon name="check" size={15} color="var(--c-secondary)" />
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
