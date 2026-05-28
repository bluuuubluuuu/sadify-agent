"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createProject,
  listProjects,
  switchProject,
  type CreateProjectResponse,
  type DriveRepoRecord,
  type ProjectSummary,
} from "../lib/api";
import { getFirebaseAuth } from "../lib/firebaseClient";
import { CreateProjectDialog } from "./CreateProjectDialog";

type Props = {
  repo: DriveRepoRecord | null;
  onRepoChanged: (repo: DriveRepoRecord | null) => void;
};

export function ProjectPanel({ repo, onRepoChanged }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [message, setMessage] = useState("Connect Google Drive before creating projects.");
  const [isBusy, setIsBusy] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    const nextProjects = repo?.available_projects ?? [];
    setProjects(nextProjects);
    setSelectedProjectId(repo?.active_project_id ?? nextProjects[0]?.project_id ?? "");
    setMessage(
      repo
        ? nextProjects.length
          ? "Project folders ready."
          : "No projects yet."
        : "Connect Google Drive before creating projects.",
    );
  }, [repo]);

  const activeProjectName = useMemo(() => {
    if (!repo?.active_project_id) {
      return "No project selected";
    }
    return repo.active_project_name ?? "No project selected";
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

  async function refreshProjects() {
    const user = getFirebaseAuth().currentUser;
    if (!user) {
      setMessage("Sign in before refreshing projects.");
      return;
    }
    if (!repo) {
      setMessage("Connect Google Drive before refreshing projects.");
      return;
    }

    setIsBusy(true);
    setMessage("Refreshing projects...");
    try {
      const idToken = await user.getIdToken();
      const response = await listProjects(idToken);
      setProjects(response.projects);
      setSelectedProjectId(response.active_project_id ?? response.projects[0]?.project_id ?? "");
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

  async function submitProject(name: string) {
    const user = getFirebaseAuth().currentUser;
    if (!user || !repo) {
      setMessage("Sign in and connect Google Drive before creating projects.");
      return;
    }

    setIsBusy(true);
    setMessage("Creating project...");
    try {
      const idToken = await user.getIdToken();
      const response = await createProject(idToken, name);
      applyProjectCreated(response);
      setDialogOpen(false);
      setMessage("Project created and selected.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create project.");
    } finally {
      setIsBusy(false);
    }
  }

  function applyProjectCreated(response: CreateProjectResponse) {
    if (!repo) {
      return;
    }
    const existing = projects.filter(
      (project) => project.project_id !== response.project.project_id,
    );
    const nextProjects = [...existing, response.project];
    setProjects(nextProjects);
    setSelectedProjectId(response.project.project_id);
    onRepoChanged(
      mergeRepoProjectState(
        repo,
        nextProjects,
        response.active_project_id,
        response.project.name,
      ),
    );
  }

  async function switchSelectedProject() {
    const user = getFirebaseAuth().currentUser;
    if (!user || !repo || !selectedProjectId) {
      setMessage("Choose a project before switching.");
      return;
    }

    setIsBusy(true);
    setMessage("Switching project...");
    try {
      const idToken = await user.getIdToken();
      const response = await switchProject(idToken, selectedProjectId);
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

  return (
    <section className="drive-panel" aria-label="Projects">
      <div className="drive-copy">
        <p className="eyebrow">Projects</p>
        <h2>{activeProjectName}</h2>
        <p>{message}</p>
      </div>

      <label className="drive-input">
        <span>Project folder</span>
        <select
          value={selectedProjectId}
          disabled={isBusy || !repo || !projects.length}
          onChange={(event) => setSelectedProjectId(event.target.value)}
        >
          {projects.length ? (
            projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.name}
              </option>
            ))
          ) : (
            <option value="">No projects yet</option>
          )}
        </select>
      </label>

      <div className="drive-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={isBusy || !repo}
          onClick={refreshProjects}
        >
          Refresh
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={isBusy || !repo || !selectedProjectId}
          onClick={switchSelectedProject}
        >
          Switch
        </button>
        <button
          type="button"
          className="primary-button"
          disabled={isBusy || !repo}
          onClick={() => setDialogOpen(true)}
        >
          New project
        </button>
      </div>

      {dialogOpen ? (
        <CreateProjectDialog
          suggestedName="Untitled Project"
          isBusy={isBusy}
          onSubmit={submitProject}
          onCancel={() => setDialogOpen(false)}
        />
      ) : null}
    </section>
  );
}
