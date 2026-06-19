"use client";

import type { ReactNode } from "react";
import type { ProjectSummary } from "../../lib/api";
import { Icon } from "../ui/Icon";
import styles from "./Sidebar.module.css";

function projectRepoUrl(folderId: string) {
  return `https://drive.google.com/drive/folders/${encodeURIComponent(folderId)}`;
}

function projectGithubUrl(repo: string) {
  return `https://github.com/${repo}`;
}

export function ProjectList({
  projects,
  activeProjectId,
  saveCounts,
  busy,
  historyNode,
  onSwitch,
  onDelete,
  onNewProject,
}: {
  projects: ProjectSummary[];
  activeProjectId: string | null;
  saveCounts?: Record<string, number>;
  busy?: boolean;
  historyNode?: ReactNode;
  onSwitch: (projectId: string) => void;
  onDelete?: (projectId: string) => void;
  onNewProject: () => void;
}) {
  return (
    <>
      {projects.map((project) => {
        const isActive = project.project_id === activeProjectId;
        const count = saveCounts?.[project.project_id];
        return (
          <div key={project.project_id} className="projectRow">
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
                aria-label={`Open Drive folder for ${project.name}`}
                title={`Open Drive folder for ${project.name}`}
              >
                <Icon name="openExternal" size={13} color="#bfdbfe" />
                <span>Drive</span>
              </a>
              {project.github_repo ? (
                <a
                  className={styles.projectRepoLink}
                  href={projectGithubUrl(project.github_repo)}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Open GitHub repo ${project.github_repo}`}
                  title={`GitHub: ${project.github_repo}`}
                >
                  <Icon name="openExternal" size={13} color="#bfdbfe" />
                  <span>GitHub</span>
                </a>
              ) : null}
              {onDelete ? (
                <button
                  type="button"
                  className="projectDeleteButton"
                  disabled={busy}
                  aria-label={`Delete project ${project.name}`}
                  title={`Delete project ${project.name}`}
                  onClick={() => onDelete(project.project_id)}
                >
                  <span aria-hidden="true">&#128465;</span>
                </button>
              ) : null}
            </div>
            {isActive ? historyNode : null}
          </div>
        );
      })}
      <button type="button" className={styles.newProjBtn} disabled={busy} onClick={onNewProject}>
        <Icon name="plus" size={16} color="#bfdbfe" />
        New project
      </button>
      <style jsx>{`
        .projectDeleteButton {
          width: 34px;
          min-width: 34px;
          border: 1px solid rgba(252, 165, 165, 0.48);
          border-radius: var(--r-sm);
          background: rgba(127, 29, 29, 0.22);
          color: #fecaca;
          cursor: pointer;
          font: inherit;
          font-size: 16px;
          transition: opacity var(--motion-fast), background var(--motion-fast);
        }
        .projectDeleteButton:hover,
        .projectDeleteButton:focus-visible {
          background: rgba(185, 28, 28, 0.5);
          outline: none;
        }
        .projectDeleteButton:disabled {
          cursor: default;
          opacity: 0.45;
        }
        @media (hover: hover) {
          .projectDeleteButton {
            opacity: 0;
          }
          .projectRow:hover .projectDeleteButton,
          .projectRow:focus-within .projectDeleteButton {
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
}
