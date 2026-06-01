"use client";

import { Icon } from "../ui/Icon";
import styles from "./chat.module.css";

type Choice = {
  id: string;
  label: string;
  is_disabled: boolean;
  status_label: string;
};

export function AnswerChips({
  choices,
  selectedIds,
  selectionMode,
  disabled,
  onToggle,
}: {
  choices: Choice[];
  selectedIds: string[];
  selectionMode: "single" | "multiple";
  disabled?: boolean;
  onToggle: (id: string) => void;
}) {
  if (!choices.length) {
    return null;
  }
  const isMulti = selectionMode === "multiple";
  return (
    <div>
      <p className={styles.selectHint}>
        {isMulti ? "Select all that apply." : "Choose one."}
      </p>
      <div
        className={styles.chips}
        role={isMulti ? "group" : "radiogroup"}
        aria-label="Answer choices"
      >
        {choices.map((choice) => {
          const selected = selectedIds.includes(choice.id);
          return (
            <button
              key={choice.id}
              type="button"
              role={isMulti ? "checkbox" : "radio"}
              aria-checked={selected}
              className={[
                styles.chip,
                selected ? styles.chipSelected : "",
                choice.is_disabled ? styles.chipDisabled : "",
              ]
                .filter(Boolean)
                .join(" ")}
              disabled={disabled || choice.is_disabled}
              onClick={() => onToggle(choice.id)}
            >
              <span
                className={[styles.chipMark, isMulti ? styles.chipMarkSquare : ""]
                  .filter(Boolean)
                  .join(" ")}
                aria-hidden="true"
              >
                {selected && isMulti ? <Icon name="check" size={12} color="#fff" /> : null}
              </span>
              <span className={styles.chipLabel}>{choice.label}</span>
              {choice.status_label ? (
                <span className={styles.chipStatus}>{choice.status_label}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
