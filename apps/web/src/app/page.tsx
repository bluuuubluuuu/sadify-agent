import { WorkspaceShell } from "../components/WorkspaceShell";
import { mockWorkspaceState } from "../lib/mockState";

export default function Home() {
  return <WorkspaceShell state={mockWorkspaceState} />;
}
