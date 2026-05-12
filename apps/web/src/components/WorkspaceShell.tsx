import { AuthPanel } from "./AuthPanel";
import type { WorkspaceState } from "../lib/mockState";
import { ChangeSummary } from "./ChangeSummary";
import { CurrentQuestion } from "./CurrentQuestion";
import { ReadinessPanel } from "./ReadinessPanel";

type Props = {
  state: WorkspaceState;
};

export function WorkspaceShell({ state }: Props) {
  return (
    <main className="workspace">
      <header className="workspace-header">
        <div>
          <p className="eyebrow">SADify</p>
          <h1>{state.projectTitle}</h1>
        </div>
        <span className="mode-pill">
          {state.mode === "guest" ? "Guest draft" : "Signed in"}
        </span>
      </header>

      <AuthPanel />

      <ChangeSummary
        summary={state.changeSummary}
        projectStatus={state.projectStatus}
      />

      <div className="workspace-grid">
        <CurrentQuestion {...state.currentQuestion} />
        <ReadinessPanel
          readinessLabel={state.readinessLabel}
          readinessScore={state.readinessScore}
          confidenceLabel={state.confidenceLabel}
          categories={state.categories}
        />
      </div>
    </main>
  );
}
