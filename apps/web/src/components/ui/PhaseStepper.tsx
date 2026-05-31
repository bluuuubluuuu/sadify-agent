import styles from "./PhaseStepper.module.css";

export function PhaseStepper({ phases, active }: { phases: string[]; active: number }) {
  return (
    <div
      className={styles.steps}
      role="status"
      aria-label={`Step ${active + 1} of ${phases.length}: ${phases[active] ?? ""}`}
    >
      {phases.map((phase, index) => (
        <div className={styles.step} key={phase}>
          <span
            className={[
              styles.num,
              index < active ? styles.done : index === active ? styles.active : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {index < active ? "✓" : index + 1}
          </span>
          <span className={index <= active ? styles.lblOn : styles.lbl}>{phase}</span>
          {index < phases.length - 1 ? <span className={styles.bar} /> : null}
        </div>
      ))}
    </div>
  );
}
