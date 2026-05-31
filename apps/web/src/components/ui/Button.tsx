"use client";

import type { ButtonHTMLAttributes, MouseEvent, ReactNode } from "react";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
  leftIcon?: ReactNode;
  children: ReactNode;
};

export function Button({
  variant = "primary",
  loading = false,
  leftIcon,
  children,
  className,
  onClick,
  disabled,
  ...rest
}: Props) {
  function handleClick(event: MouseEvent<HTMLButtonElement>) {
    if (loading || disabled) {
      return;
    }
    addRipple(event);
    onClick?.(event);
  }

  return (
    <button
      className={[styles.btn, styles[variant], loading ? styles.loading : "", className ?? ""]
        .filter(Boolean)
        .join(" ")}
      onClick={handleClick}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className={styles.spin} aria-hidden="true" /> : leftIcon}
      <span>{children}</span>
    </button>
  );
}

function addRipple(event: MouseEvent<HTMLButtonElement>) {
  if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
    return;
  }
  const button = event.currentTarget;
  const rect = button.getBoundingClientRect();
  const diameter = Math.max(rect.width, rect.height);
  const circle = document.createElement("span");
  circle.className = styles.ripple;
  circle.style.width = circle.style.height = `${diameter}px`;
  circle.style.left = `${event.clientX - rect.left - diameter / 2}px`;
  circle.style.top = `${event.clientY - rect.top - diameter / 2}px`;
  button.appendChild(circle);
  window.setTimeout(() => circle.remove(), 600);
}
