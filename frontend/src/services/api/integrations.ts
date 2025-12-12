import { api } from "./client";
import { z } from "zod";

export type GitLabCommitRequest = {
  testcases_job_id: string;
  repository: string;
  branch?: string;
  commit_message?: string;
  create_mr?: boolean;
  target_branch?: string | null;
  mr_title?: string | null;
  mr_description?: string | null;
};

export async function commitToGitLab(data: GitLabCommitRequest) {
  const res = await api.post("/integrations/gitlab/commit", data);
  return res.data as { job_id: string; status: string; message?: string; testcases_count?: number };
}

export async function listGitlabProjects() {
  const res = await api.get("/integrations/gitlab/projects");
  return z.array(z.record(z.any())).parse(res.data);
}

export async function listGitlabBranches(projectId: string) {
  const res = await api.get(`/integrations/gitlab/branches/${projectId}`);
  return z.array(z.record(z.any())).parse(res.data);
}

