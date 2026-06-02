"use client";

import { Icon } from "../ui/Icon";
import { CoverageChecklist, type CoverageCategory } from "./CoverageChecklist";
import styles from "./ReadinessPane.module.css";

export function ReadinessPane({
  score,
  label,
  confidence,
  categories,
  understandingSummary,
}: {
  score: number;
  label: string;
  confidence: "Low" | "Medium" | "High";
  categories: CoverageCategory[];
  understandingSummary: string;
}) {
  const confClass =
    confidence === "High"
      ? styles.confHigh
      : confidence === "Medium"
        ? styles.confMedium
        : styles.confLow;

  return (
    <div className={styles.pane}>
      <div className={styles.title}>SAD readiness</div>
      <div className={styles.ringBox}>
        <div
          className={styles.ring}
          style={{ background: `conic-gradient(var(--c-accent) ${score}%, var(--c-border) 0)` }}
        >
          <div className={styles.ringInner}>{score}%</div>
        </div>
        <div className={styles.rmeta}>
          <b>{label}</b>
          <span className={`${styles.conf} ${confClass}`}>{confidence} confidence</span>
        </div>
      </div>

      <div className={styles.title}>Coverage</div>
      <CoverageChecklist categories={categories} />

      {understandingSummary ? (
        <details className={styles.summary}>
          <summary>
            <Icon name="eye" size={14} color="var(--c-primary)" />
            What I understand so far
          </summary>
          <p>{understandingSummary}</p>
        </details>
      ) : null}
    </div>
  );
}

export function PreviewPlaceholder({ text }: { text: string }) {
  return (
    <div className={styles.placeholder}>
      <div className={styles.phBox}>
        <Icon name="fileText" size={26} color="#94a3b8" />
      </div>
      <span>{text}</span>
    </div>
  );
}
