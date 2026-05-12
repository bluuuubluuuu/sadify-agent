import type { CategoryStatus, WorkspaceState } from "../lib/mockState";

type Props = Pick<
  WorkspaceState,
  "readinessLabel" | "readinessScore" | "confidenceLabel" | "categories"
>;

const statusLabel: Record<CategoryStatus, string> = {
  complete: "Ready",
  partial: "Started",
  missing: "Needed",
};

export function ReadinessPanel({
  readinessLabel,
  readinessScore,
  confidenceLabel,
  categories,
}: Props) {
  return (
    <aside className="readiness-panel" aria-label="Readiness and question areas">
      <p className="eyebrow">Readiness</p>
      <strong>{readinessLabel}</strong>
      <div className="readiness-score">
        <span>{readinessScore}%</span>
        <small>{confidenceLabel} confidence</small>
      </div>

      <div className="meter" aria-hidden="true">
        <span style={{ width: `${readinessScore}%` }} />
      </div>

      <div className="category-list" aria-label="Questionnaire sections">
        {categories.map((category) => (
          <div key={category.label} className={`category ${category.status}`}>
            <span>{category.label}</span>
            <small>{statusLabel[category.status]}</small>
          </div>
        ))}
      </div>
    </aside>
  );
}
