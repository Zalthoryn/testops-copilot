import { api } from "./client";
import { jobResponse, jobStatusResponse } from "../../types/api";

export type UIAutotestsRequest = {
  manual_testcases_ids: string[];
  framework?: string;
  browsers?: string[];
  base_url?: string;
  headless?: boolean;
  priority_filter?: string[];
};

export type APIAutotestsRequest = {
  manual_testcases_ids: string[];
  openapi_url?: string | null;
  sections: string[];
  base_url?: string;
  auth_token?: string | null;
  test_framework?: string;
  http_client?: string;
};

export async function generateUIAutotests(data: UIAutotestsRequest) {
  const res = await api.post("/autotests/ui", data);
  return jobResponse.parse(res.data);
}

export async function generateAPIAutotests(data: APIAutotestsRequest) {
  const res = await api.post("/autotests/api", data);
  return jobResponse.parse(res.data);
}

export async function getAutotestJob(jobId: string) {
  const res = await api.get(`/autotests/${jobId}`);
  return jobStatusResponse.parse(res.data);
}

export async function downloadAutotests(jobId: string) {
  const res = await api.get(`/autotests/${jobId}/download`, { responseType: "blob" });
  return res.data as Blob;
}

