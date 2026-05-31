import styles from "./ThinkingDots.module.css";

export function ThinkingDots({ label = "Assistant is thinking" }: { label?: string }) {
  return (
    <span className={styles.wrap} role="status" aria-label={label}>
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className={styles.dot} />
    </span>
  );
}
