"use client";

import { type KeyboardEvent, type ReactNode } from "react";
import { Icon } from "../ui/Icon";
import { AutoTextarea } from "../ui/AutoTextarea";
import styles from "./chat.module.css";

export function Composer({
  value,
  onChange,
  onSubmit,
  onAttachClick,
  attaching,
  placeholder,
  disabled,
  canSubmit,
  chips,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onAttachClick?: () => void;
  attaching?: boolean;
  placeholder?: string;
  disabled?: boolean;
  canSubmit?: boolean;
  chips?: ReactNode;
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSubmit && !disabled) {
        onSubmit();
      }
    }
  }

  return (
    <div className={styles.composer}>
      {chips}
      <div className={styles.inputRow}>
        {onAttachClick ? (
          <button
            type="button"
            className={styles.attachBtn}
            aria-label="Attach files"
            disabled={attaching}
            onClick={onAttachClick}
          >
            <Icon name="paperclip" size={18} />
          </button>
        ) : null}
        <AutoTextarea
          className={styles.input}
          maxHeight={200}
          value={value}
          placeholder={placeholder ?? "Type your answer…"}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className={styles.sendBtn}
          aria-label="Send"
          disabled={!canSubmit || disabled}
          onClick={onSubmit}
        >
          <Icon name="arrowRight" size={20} color="#fff" />
        </button>
      </div>
    </div>
  );
}
