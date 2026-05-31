import styles from "./StepProgress.module.css";

export type StepState = "pending" | "active" | "done";

export function StepProgress({
  steps,
}: {
  steps: Array<{ label: string; state: StepState }>;
}) {
  return (
    <ul className={styles.list}>
      {steps.map((step) => (
        <li key={step.label} className={[styles.row, styles[step.state]].join(" ")}>
          <span className={styles.icon} aria-hidden="true">
            {step.state === "done" ? "✓" : step.state === "active" ? (
              <span className={styles.spin} />
            ) : null}
          </span>
          <span>{step.label}</span>
        </li>
      ))}
    </ul>
  );
}
