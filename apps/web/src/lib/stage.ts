/**
 * Derives which workspace stage is active so the AppShell knows which pane to
 * emphasise. See docs/superpowers/specs/2026-05-31-sadify-ui-redesign-design.md.
 *
 * onboarding -> no analysis yet (chat welcome leads)
 * clarify    -> analysis in progress, readiness < 100 (chat leads)
 * review     -> a SAD preview exists (preview leads)
 */
export type Stage = "onboarding" | "clarify" | "review";

export function deriveStage(input: {
  hasAnalysis: boolean;
  readinessScore: number;
  hasPreview: boolean;
}): Stage {
  if (input.hasPreview) {
    return "review";
  }
  if (input.hasAnalysis) {
    return "clarify";
  }
  return "onboarding";
}
