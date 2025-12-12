import { useState, useCallback } from "react";
import { usePolling } from "./usePolling";
import { JobStatus } from "../types/api";

type BaseJob = {
  job_id: string;
  status: JobStatus;
  message?: string | null;
  estimated_time?: number | null;
  created_at?: string;
  updated_at?: string | null;
};

type Fetcher<T extends BaseJob> = (jobId: string) => Promise<T>;

export const useJobWatcher = <T extends BaseJob = BaseJob>(
  jobId: string | null,
  fetcher: Fetcher<T>,
  onDone?: () => void
) => {
  const [job, setJob] = useState<T | null>(null);

  const poll = useCallback(async () => {
    if (!jobId) return;
    const result = await fetcher(jobId);
    setJob(result);
    if (["completed", "failed"].includes(result.status) && onDone) {
      onDone();
    }
  }, [fetcher, jobId, onDone]);

  usePolling(poll, 2000, Boolean(jobId) && (!job || job.status === "processing"));

  return { job, setJob };
};
