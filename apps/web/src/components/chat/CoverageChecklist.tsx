import { Icon } from "../ui/Icon";
import styles from "./ReadinessPane.module.css";

// Accepts both the stable questionnaire status union and the legacy raw
// (Gemini/fallback) union, so the checklist renders whichever the workspace
// passes. The workspace prefers questionnaire.categories when present.
export type CoverageStatus =
  | "ready"
  | "in_progress"
  | "needed"
  | "needs_later_confirmation"
  | "complete"
  | "partial"
  | "missing";

export type CoverageCategory = {
  id: string;
  label: string;
  status: CoverageStatus;
  visibility?:
    | "main"
    | "already_understood"
    | "completed"
    | "suggested"
    | "not_applicable";
};

function mark(status: CoverageStatus) {
  switch (status) {
    case "ready":
    case "complete":
      return { name: "checkCircle", color: "var(--c-accent)" } as const;
    case "in_progress":
    case "partial":
      return { name: "halfCircle", color: "var(--c-warn)" } as const;
    case "needs_later_confirmation":
      return { name: "clock", color: "var(--c-secondary)" } as const;
    case "needed":
    case "missing":
    default:
      return { name: "circle", color: "#cbd5e1" } as const;
  }
}

export function CoverageChecklist({ categories }: { categories: CoverageCategory[] }) {
  if (!categories.length) {
    return null;
  }
  return (
    <div className={styles.coverage}>
      {categories.map((category) => {
        const dim =
          category.visibility === "not_applicable" ||
          category.status === "needed" ||
          category.status === "missing";
        const icon = mark(category.status);
        return (
          <div
            key={category.id}
            className={[styles.cov, dim ? styles.covMiss : ""].filter(Boolean).join(" ")}
          >
            <Icon name={icon.name} size={16} color={icon.color} />
            <span>{category.label}</span>
          </div>
        );
      })}
    </div>
  );
}
