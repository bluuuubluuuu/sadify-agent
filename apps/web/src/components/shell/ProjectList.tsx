"use client";

import type { ReactNode } from "react";
import type { ProjectSummary } from "../../lib/api";
import { Icon } from "../ui/Icon";
import styles from "./Sidebar.module.css";

function projectRepoUrl(folderId: string) {
  return `https://drive.google.com/drive/folders/${encodeURIComponent(folderId)}`;
}

export function ProjectList({
  projects,
  activeProjectId,
  saveCounts,
  busy,
  historyNode,
  onSwitch,
  onNewProject,
}: {
  projects: ProjectSummary[];
  activeProjectId: string | null;
  saveCounts?: Record<string, number>;
  busy?: boolean;
  historyNode?: ReactNode;
  onSwitch: (projectId: string) => void;
  onNewProject: () => void;
}) {
  return (
    <>
      {projects.map((project) => {
        const isActive = project.project_id === activeProjectId;
        const count = saveCounts?.[project.project_id];
        return (
          <div key={project.project_id}>
            <div className={styles.projLine}>
              <button
                type="button"
                className={[styles.projItem, isActive ? styles.projItemActive : ""]
                  .filter(Boolean)
                  .join(" ")}
                disabled={busy}
                aria-current={isActive ? "true" : undefined}
                onClick={() => onSwitch(project.project_id)}
              >
                <Icon name="folder" size={18} color="#fff" />
                <span className={styles.projName}>{project.name}</span>
                {typeof count === "number" ? (
                  <span className={styles.projCount}>{count} saves</span>
                ) : null}
              </button>
              <a
                className={styles.projectRepoLink}
                href={projectRepoUrl(project.drive_folder_id)}
                target="_blank"
                rel="noreferrer"
                aria-label={`Open project repo for ${project.name}`}
                title={`Open project repo for ${project.name}`}
              >
                <Icon name="openExternal" size={13} color="#bfdbfe" />
                <span>Repo</span>
              </a>
            </div>
            {isActive ? historyNode : null}
          </div>
        );
      })}
      <button type="button" className={styles.newProjBtn} disabled={busy} onClick={onNewProject}>
        <Icon name="plus" size={16} color="#bfdbfe" />
        New project
      </button>
    </>
  );
}
