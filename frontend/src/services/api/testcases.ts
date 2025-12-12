import { api } from "./client";
import { jobResponse, jobStatusResponse } from "../../types/api";
import { z } from "zod";

export type ManualUIGenerationRequest = {
  project_name?: string;
  requirements: string;
  test_blocks: string[];
  target_count: number;
  priority: "CRITICAL" | "NORMAL" | "LOW";
  owner?: string;
  include_screenshots?: boolean;
};

export type ManualAPIGenerationRequest = {
  openapi_url?: string | null;
  openapi_content?: string | null;
  sections: string[];
  auth_type?: string;
  target_count: number;
  priority?: "CRITICAL" | "NORMAL" | "LOW";
};

export async function generateManualUI(data: ManualUIGenerationRequest) {
  const res = await api.post("/testcases/manual/ui", data);
  return jobResponse.parse(res.data);
}

export async function generateManualAPI(data: ManualAPIGenerationRequest) {
  const res = await api.post("/testcases/manual/api", data);
  return jobResponse.parse(res.data);
}

export async function getTestcaseJob(jobId: string) {
  const res = await api.get(`/testcases/${jobId}`);
  return jobStatusResponse.parse(res.data);
}

export async function downloadTestcases(jobId: string) {
  const res = await api.get(`/testcases/${jobId}/download`, { responseType: "blob" });
  return res.data as Blob;
}

export async function listTestcaseJobs(params?: { status?: string; limit?: number; offset?: number }) {
  const res = await api.get("/testcases/", { params });
  return z.array(jobResponse).parse(res.data);
}

