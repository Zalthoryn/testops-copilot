import { api } from "./client";
import { jobResponse } from "../../types/api";
import { z } from "zod";

export async function checkStandards(files: File[], checks: string[]) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  checks.forEach((check) => form.append("checks", check));
  const res = await api.post("/standards/check", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return jobResponse.parse(res.data);
}

export async function getStandardsJob(jobId: string) {
  const res = await api.get(`/standards/${jobId}`);
  return jobResponse.extend({ testcases: z.any().optional() }).parse(res.data);
}

export async function downloadStandardsReport(jobId: string) {
  const res = await api.get(`/standards/${jobId}/report`, { responseType: "blob" });
  return res.data as Blob;
}

