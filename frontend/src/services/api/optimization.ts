import { api } from "./client";
import { jobResponse } from "../../types/api";
import { z } from "zod";

export type OptimizationRequest = {
  repository_url?: string | null;
  test_files?: { filename: string; content: string }[];
  requirements?: string | null;
  checks: string[];
  optimization_level?: "conservative" | "moderate" | "aggressive";
};

export async function analyzeOptimization(data: OptimizationRequest) {
  const res = await api.post("/optimization/analyze", data);
  return jobResponse.parse(res.data);
}

export async function getOptimizationJob(jobId: string) {
  const res = await api.get(`/optimization/${jobId}`);
  return jobResponse.extend({ recommendations: z.any().optional() }).parse(res.data);
}

export async function downloadOptimized(jobId: string) {
  const res = await api.get(`/optimization/${jobId}/download`, { responseType: "blob" });
  return res.data as Blob;
}

