"use client";

import { useState } from "react";
import type { DriveRepoRecord } from "../../lib/api";
import { useDriveRepo } from "../../lib/hooks/useDriveRepo";
import { useProjects } from "../../lib/hooks/useProjects";
import { useSaveHistory } from "../../lib/hooks/useSaveHistory";
import { Icon } from "../ui/Icon";
import { Button } from "../ui/Button";
import { SetupChecklist } from "./SetupChecklist";
import { ProjectList } from "./ProjectList";
import { SaveHistory } from "./SaveHistory";
import { AccountMenu } from "./AccountMenu";
import { CreateProjectDialog } from "./CreateProjectDialog";
import styles from "./Sidebar.module.css";

export function Sidebar({
  displayName,
  email,
  isSignedIn,
  repo,
  onRepoChanged,
  historyRefreshKey,
  onNewSad,
  onSignOut,
}: {
  displayName: string | null;
  email: string | null;
  isSignedIn: boolean;
  repo: DriveRepoRecord | null;
  onRepoChanged: (repo: DriveRepoRecord | null) => void;
  historyRefreshKey: number;
  onNewSad: () => void;
  onSignOut: () => void;
}) {
  const drive = useDriveRepo(onRepoChanged);
  const projectsHook = useProjects(repo, onRepoChanged);
  const history = useSaveHistory(repo?.active_project_id ?? null, historyRefreshKey);
  const [dialogOpen, setDialogOpen] = useState(false);
  const connected = Boolean(repo && !repo.saves_blocked);

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

      <div className={styles.label}>Setup</div>
      <SetupChecklist
        isSignedIn={isSignedIn}
        connected={connected}
        repoName={repo?.repo_folder_name}
        onConnectDrive={() => drive.connect()}
      />

      {repo ? (
        <>
          <div className={styles.label}>Projects</div>
          <ProjectList
            projects={projectsHook.projects}
            activeProjectId={repo.active_project_id}
            busy={projectsHook.isBusy}
            onSwitch={(projectId) => projectsHook.switchTo(projectId)}
            onNewProject={() => setDialogOpen(true)}
            historyNode={<SaveHistory saves={history.saves} message={history.message} />}
          />
        </>
      ) : null}

      <AccountMenu
        name={displayName}
        email={email}
        repo={repo}
        onDisconnect={() => drive.disconnect()}
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
