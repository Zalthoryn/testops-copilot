import { z } from "zod";

export const testPriority = z.enum(["CRITICAL", "NORMAL", "LOW"]);
export type TestPriority = z.infer<typeof testPriority>;

export const testType = z.enum(["manual_ui", "manual_api", "auto_ui", "auto_api"]);
export type TestType = z.infer<typeof testType>;

export const jobStatus = z.enum(["pending", "processing", "completed", "failed", "cancelled"]);
export type JobStatus = z.infer<typeof jobStatus>;

export const testCaseDTO = z.object({
  id: z.string().uuid(),
  title: z.string(),
  feature: z.string(),
  story: z.string(),
  priority: testPriority,
  steps: z.array(z.string()),
  expected_result: z.string(),
  python_code: z.string(),
  test_type: testType,
  owner: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime().nullable().optional(),
});
export type TestCaseDTO = z.infer<typeof testCaseDTO>;

export const jobResponse = z.object({
  job_id: z.string().uuid(),
  status: jobStatus,
  message: z.string().nullable().optional(),
  estimated_time: z.number().nullable().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime().nullable().optional(),
});
export type JobResponse = z.infer<typeof jobResponse>;

export const jobStatusResponse = jobResponse.extend({
  testcases: z.array(testCaseDTO).default([]),
  download_url: z.string().optional().nullable(),
  metrics: z.record(z.any()).optional().nullable(),
});
export type JobStatusResponse = z.infer<typeof jobStatusResponse>;

export const standardsViolation = z.object({
  file: z.string(),
  line: z.number(),
  severity: z.enum(["error", "warning", "info"]),
  rule: z.string(),
  message: z.string(),
  suggested_fix: z.string(),
});

export const standardsReport = z.object({
  job_id: z.string().uuid(),
  status: jobStatus,
  total_files: z.number(),
  total_violations: z.number(),
  violations_by_severity: z.record(z.number()),
  violations: z.array(standardsViolation),
  generated_at: z.string().datetime(),
});
export type StandardsReport = z.infer<typeof standardsReport>;

export const optimizationResult = z.object({
  job_id: z.string().uuid(),
  status: jobStatus,
  analysis: z.record(z.any()),
  recommendations: z.array(z.record(z.any())),
  optimized_testcases: z.array(testCaseDTO),
  generated_at: z.string().datetime(),
});
export type OptimizationResult = z.infer<typeof optimizationResult>;

export const configResponse = z.object({
  llm_model: z.string(),
  compute_endpoint: z.string(),
  gitlab_configured: z.boolean(),
  llm_available: z.boolean(),
  compute_available: z.boolean(),
  environment: z.string(),
});
export type ConfigResponse = z.infer<typeof configResponse>;

export const computeValidationResponse = z.object({
  valid: z.boolean(),
  endpoint: z.string(),
  available_resources: z.array(z.string()),
  error: z.string().nullable().optional(),
});
export type ComputeValidationResponse = z.infer<typeof computeValidationResponse>;

