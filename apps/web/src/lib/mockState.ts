export type Choice = {
  id: string;
  label: string;
  is_disabled?: boolean;
  status_label?: string;
};

export type CategoryStatus =
  | "complete"
  | "partial"
  | "missing"
  | "ready"
  | "in_progress"
  | "needed"
  | "needs_later_confirmation";

export type WorkspaceState = {
  projectTitle: string;
  mode: "guest" | "signed_in";
  readinessLabel: string;
  readinessScore: number;
  confidenceLabel: "Low" | "Medium" | "High";
  currentQuestion: {
    text: string;
    whyThisMatters: string;
    choices: Choice[];
  };
  categories: Array<{
    label: string;
    status: CategoryStatus;
    progress?: number;
    questionsAnswered?: number;
    questionsTotal?: number;
    isActive?: boolean;
  }>;
  changeSummary: string;
  projectStatus: string[];
};

export const mockWorkspaceState: WorkspaceState = {
  projectTitle: "Guest draft",
  mode: "guest",
  readinessLabel: "No analysis yet",
  readinessScore: 0,
  confidenceLabel: "Medium",
  currentQuestion: {
    text: "",
    whyThisMatters: "",
    choices: [],
  },
  categories: [],
  changeSummary: "No analysis yet. No project files saved.",
  projectStatus: [
    "Guest draft active",
    "Questions in progress",
    "SAD preview not generated yet",
    "Project repo not connected",
  ],
};
