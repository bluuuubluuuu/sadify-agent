"use client";

import { useEffect, useRef, useState } from "react";
import type { DriveRepoRecord, SadSaveSummary } from "../../lib/api";
import { useDriveRepo } from "../../lib/hooks/useDriveRepo";
import { useProjects } from "../../lib/hooks/useProjects";
import { useSaveHistory } from "../../lib/hooks/useSaveHistory";
import { Icon } from "../ui/Icon";
import { Button } from "../ui/Button";
import { ProjectList } from "./ProjectList";
import { SaveHistory } from "./SaveHistory";
import { AccountMenu } from "./AccountMenu";
import { CreateProjectDialog } from "./CreateProjectDialog";
import styles from "./Sidebar.module.css";

export function Sidebar({
  displayName,
  email,
  repo,
  onRepoChanged,
  historyRefreshKey,
  onNewSad,
  onDeleteProject,
  onCreateGithubIssues,
  onSignIn,
  onSignOut,
}: {
  displayName: string | null;
  email: string | null;
  repo: DriveRepoRecord | null;
  onRepoChanged: (repo: DriveRepoRecord | null) => void;
  historyRefreshKey: number;
  onNewSad: () => void;
  onDeleteProject: (projectId: string) => void;
  onCreateGithubIssues: (save: SadSaveSummary) => void;
  onSignIn: () => void;
  onSignOut: () => void;
}) {
  const drive = useDriveRepo(onRepoChanged);
  const projectsHook = useProjects(repo, onRepoChanged);
  const history = useSaveHistory(repo?.active_project_id ?? null, historyRefreshKey);
  const [dialogOpen, setDialogOpen] = useState(false);
  const refreshedGrantRef = useRef<string | null>(null);

  // The Drive-status snapshot's available_projects can be stale for fields set
  // after connect (e.g. github_repo). Pull the source-of-truth project list once
  // per grant so the sidebar GitHub chip (and active repo) survive reloads.
  useEffect(() => {
    const grantId = repo?.grant_id ?? null;
    if (grantId && refreshedGrantRef.current !== grantId) {
      refreshedGrantRef.current = grantId;
      void projectsHook.refresh();
    }
  }, [repo?.grant_id]);

  async function handleCreate(name: string) {
    await projectsHook.create(name);
    setDialogOpen(false);
  }

  return (
    <div className={styles.inner}>
      <div className={styles.logo}>
        <Icon name="sparkle" size={20} color="#fff" />
        SADify
      </div>
      <Button
        variant="primary"
        className={styles.newBtn}
        leftIcon={<Icon name="edit" size={18} color="#fff" />}
        onClick={onNewSad}
        style={{ background: "var(--c-accent)", boxShadow: "0 4px 14px rgba(5,150,105,0.3)" }}
      >
        New SAD
      </Button>

      {repo ? (
        <>
          <div className={styles.label}>Projects</div>
          <ProjectList
            projects={projectsHook.projects}
            activeProjectId={repo.active_project_id}
            busy={projectsHook.isBusy}
            onSwitch={(projectId) => projectsHook.switchTo(projectId)}
            onDelete={onDeleteProject}
            onNewProject={() => setDialogOpen(true)}
            historyNode={
              <SaveHistory
                saves={history.saves}
                message={history.message}
                onCreateGithubIssues={onCreateGithubIssues}
              />
            }
          />
        </>
      ) : null}

      <AccountMenu
        name={displayName}
        email={email}
        repo={repo}
        onConnect={() => drive.connect()}
        onDisconnect={() => drive.disconnect()}
        onSignIn={onSignIn}
        onSignOut={onSignOut}
      />

      {dialogOpen ? (
        <CreateProjectDialog
          suggestedName="Untitled Project"
          isBusy={projectsHook.isBusy}
          onSubmit={handleCreate}
          onCancel={() => setDialogOpen(false)}
        />
      ) : null}
    </div>
  );
}
