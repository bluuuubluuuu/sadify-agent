"use client";

import { useEffect, useState } from "react";
import {
  createProject,
  listProjects,
  switchProject,
  type DriveRepoRecord,
  type ProjectSummary,
} from "../api";
import { getFirebaseAuth } from "../firebaseClient";

/**
 * Preserves ProjectPanel's list/switch/create logic and the repo-merge so the
 * shell's driveRepo stays the single source of truth.
 */
export function useProjects(
  repo: DriveRepoRecord | null,
  onRepoChanged: (repo: DriveRepoRecord | null) => void,
) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setProjects(repo?.available_projects ?? []);
  }, [repo]);

  function mergeRepoProjectState(
    currentRepo: DriveRepoRecord,
    nextProjects: ProjectSummary[],
    activeProjectId: string | null,
    activeProjectName: string | null,
  ): DriveRepoRecord {
    return {
      ...currentRepo,
      active_project_id: activeProjectId,
      active_project_name: activeProjectName,
      available_projects: nextProjects,
    };
  }

  async function refresh() {
    const user = getFirebaseAuth().currentUser;
    if (!user || !repo) {
      return;
    }
    setIsBusy(true);
    setMessage("Refreshing projects...");
    try {
      const idToken = await user.getIdToken();
      const response = await listProjects(idToken);
      setProjects(response.projects);
      onRepoChanged(
        mergeRepoProjectState(
          repo,
          response.projects,
          response.active_project_id,
          response.active_project_name,
        ),
      );
      setMessage(response.projects.length ? "Project list refreshed." : "No projects yet.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not refresh projects.");
    } finally {
      setIsBusy(false);
    }
  }

  async function switchTo(projectId: string) {
    const user = getFirebaseAuth().currentUser;
    if (!user || !repo || !projectId) {
      return;
    }
    setIsBusy(true);
    setMessage("Switching project...");
    try {
      const idToken = await user.getIdToken();
      const response = await switchProject(idToken, projectId);
      onRepoChanged(
        mergeRepoProjectState(
          repo,
          projects,
          response.active_project_id,
          response.active_project_name,
        ),
      );
      setMessage("Project selected.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not switch project.");
    } finally {
      setIsBusy(false);
    }
  }

  async function create(name: string) {
    const user = getFirebaseAuth().currentUser;
    if (!user || !repo) {
      return;
    }
    setIsBusy(true);
    setMessage("Creating project...");
    try {
      const idToken = await user.getIdToken();
      const response = await createProject(idToken, name);
      const existing = projects.filter(
        (project) => project.project_id !== response.project.project_id,
      );
      const nextProjects = [...existing, response.project];
      setProjects(nextProjects);
      onRepoChanged(
        mergeRepoProjectState(
          repo,
          nextProjects,
          response.active_project_id,
          response.project.name,
        ),
      );
      setMessage("Project created and selected.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create project.");
    } finally {
      setIsBusy(false);
    }
  }

  return { projects, isBusy, message, refresh, switchTo, create };
}
