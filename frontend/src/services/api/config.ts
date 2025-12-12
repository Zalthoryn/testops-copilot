import { api } from "./client";
import { configResponse, computeValidationResponse } from "../../types/api";

export async function getConfig() {
  const res = await api.get("/config/");
  return configResponse.parse(res.data);
}

export async function validateCompute(data: { token?: string; key_id?: string; secret?: string }) {
  const res = await api.post("/config/compute/validate", data);
  return computeValidationResponse.parse(res.data);
}

export async function validateGitlab(data: { token: string; project_id: string; base_url?: string }) {
  const res = await api.post("/config/gitlab/validate", null, { params: data });
  return res.data as { valid: boolean; authenticated: boolean; project?: any; error?: string };
}

export async function validateLLM(data: { api_key: string; model?: string; base_url?: string }) {
  const res = await api.post("/config/llm/validate", null, { params: data });
  return res.data as { valid: boolean; model: string; base_url: string };
}

export async function getHealthDetailed() {
  const res = await api.get("/config/health/detailed");
  return res.data as Record<string, any>;
}

