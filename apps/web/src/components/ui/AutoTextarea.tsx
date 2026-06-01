"use client";

import { useEffect, useRef, type TextareaHTMLAttributes } from "react";

/**
 * Textarea that grows with its content (ChatGPT-style) up to `maxHeight`, then
 * locks and scrolls internally so older lines scroll off the top. No visible
 * scrollbar until the cap is reached.
 */
export function AutoTextarea({
  value,
  maxHeight = 200,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { maxHeight?: number }) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) {
      return;
    }
    el.style.height = "auto";
    const next = Math.min(el.scrollHeight, maxHeight);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [value, maxHeight]);

  return <textarea ref={ref} value={value} rows={1} {...props} />;
}
