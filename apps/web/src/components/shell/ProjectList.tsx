"use client";

import type { ReactNode } from "react";
import type { ProjectSummary } from "../../lib/api";
import { Icon } from "../ui/Icon";
import styles from "./Sidebar.module.css";

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
