export function shouldWriteSnapshot(args: {
  isSignedIn: boolean;
  activeProjectId: string | null;
  scheduledProjectId: string | null;
  hasAnalysis: boolean;
  restoring: boolean;
}): boolean {
  const {
    isSignedIn,
    activeProjectId,
    scheduledProjectId,
    hasAnalysis,
    restoring,
  } = args;
  if (!isSignedIn || !activeProjectId || !hasAnalysis || restoring) {
    return false;
  }
  return scheduledProjectId === activeProjectId;
}
