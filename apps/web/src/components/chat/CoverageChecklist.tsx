import { Icon } from "../ui/Icon";
import styles from "./ReadinessPane.module.css";

type Category = {
  id: string;
  label: string;
  status: "complete" | "partial" | "missing";
};

export function CoverageChecklist({ categories }: { categories: Category[] }) {
  if (!categories.length) {
    return null;
  }
  return (
    <div className={styles.coverage}>
      {categories.map((category) => (
        <div
          key={category.id}
          className={[styles.cov, category.status === "missing" ? styles.covMiss : ""]
            .filter(Boolean)
            .join(" ")}
        >
          {category.status === "complete" ? (
            <Icon name="checkCircle" size={16} color="var(--c-accent)" />
          ) : category.status === "partial" ? (
            <Icon name="halfCircle" size={16} color="var(--c-warn)" />
          ) : (
            <Icon name="circle" size={16} color="#cbd5e1" />
          )}
          <span>{category.label}</span>
        </div>
      ))}
    </div>
  );
}
