export type Choice = {
  id: string;
  label: string;
};

export type CategoryStatus = "complete" | "partial" | "missing";

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
  }>;
  changeSummary: string;
  projectStatus: string[];
};

export const mockWorkspaceState: WorkspaceState = {
  projectTitle: "Guest draft",
  mode: "guest",
  readinessLabel: "Getting started",
  readinessScore: 35,
  confidenceLabel: "Medium",
  currentQuestion: {
    text: "Who will use this system most often?",
    whyThisMatters: "This helps SADify shape roles, permissions, and the daily workflow.",
    choices: [
      { id: "frontline", label: "Frontline staff" },
      { id: "supervisors", label: "Supervisors or approvers" },
      { id: "managers", label: "Managers or report viewers" },
      { id: "not_sure", label: "Not sure yet" },
    ],
  },
  categories: [
    { label: "Problem", status: "partial" },
    { label: "Users and roles", status: "missing" },
    { label: "Workflow", status: "missing" },
    { label: "Data and files", status: "missing" },
    { label: "Reports", status: "missing" },
  ],
  changeSummary: "1 draft started. No project files saved yet.",
  projectStatus: [
    "Guest draft active",
    "Questions in progress",
    "SAD preview not generated yet",
    "Project repo not connected",
  ],
};
