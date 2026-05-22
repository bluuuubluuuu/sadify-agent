import type { CategoryStatus, WorkspaceState } from "../lib/mockState";

type Props = Pick<
  WorkspaceState,
  "readinessLabel" | "readinessScore" | "confidenceLabel" | "categories"
>;

const statusLabel: Record<CategoryStatus, string> = {
  complete: "Ready",
  partial: "Started",
  missing: "Needed",
  ready: "Ready",
  in_progress: "In progress",
  needed: "Needed",
  needs_later_confirmation: "Confirm later",
};

export function ReadinessPanel({
  readinessLabel,
  readinessScore,
  confidenceLabel,
  categories,
}: Props) {
  return (
    <aside className="readiness-panel" aria-label="Readiness and question areas">
      <p className="eyebrow">Overall readiness</p>
      <strong>{readinessLabel}</strong>
      <div className="readiness-score">
        <span>{readinessScore}%</span>
      </div>

      <div className="meter" aria-hidden="true">
        <span style={{ width: `${readinessScore}%` }} />
      </div>

      <div className="category-list" aria-label="Questionnaire sections">
        {categories.map((category) => (
          <div key={category.label} className={`category ${category.status}`}>
            <span>
              {category.label}
              {category.isActive ? <small className="active-tag">Active</small> : null}
            </span>
            <small>{statusLabel[category.status]}</small>
          </div>
        ))}
      </div>

      <details className="analysis-diagnostics">
        <summary>Analysis diagnostics</summary>
        <p>AI check: {confidenceToBadge(confidenceLabel)}</p>
      </details>
    </aside>
  );
}

function confidenceToBadge(confidenceLabel: "Low" | "Medium" | "High") {
  if (confidenceLabel === "High") {
    return "strong";
  }
  if (confidenceLabel === "Medium") {
    return "usable";
  }
  return "needs review";
}
