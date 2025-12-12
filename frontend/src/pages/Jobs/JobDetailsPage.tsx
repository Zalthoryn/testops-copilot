import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getTestcaseJob } from "../../services/api/testcases";
import { getAutotestJob } from "../../services/api/autotests";
import { getOptimizationJob } from "../../services/api/optimization";
import { getStandardsJob } from "../../services/api/standards";
import GlassCard from "../../components/common/GlassCard";
import SectionHeader from "../../components/common/SectionHeader";
import { JobResponse } from "../../types/api";

const JobDetailsPage = () => {
  const { jobId } = useParams<{ jobId: string }>();

  const query = useQuery<JobResponse>({
    queryKey: ["job", jobId],
    queryFn: async () => {
      if (!jobId) throw new Error("Job ID required");
      // Try in order: testcases -> autotests -> standards -> optimization
      try {
        return await getTestcaseJob(jobId);
      } catch {
        try {
          return await getAutotestJob(jobId);
        } catch {
          try {
            return await getStandardsJob(jobId);
          } catch {
            return await getOptimizationJob(jobId);
          }
        }
      }
    },
    enabled: Boolean(jobId),
    refetchInterval: (query) => (query.state.data?.status === "processing" ? 2000 : false),
  });

  return (
    <GlassCard>
      <SectionHeader title={`Job ${jobId}`} />
      {query.isLoading && <div className="muted">Загрузка...</div>}
      {query.data && (
        <>
          <div className={`status ${query.data.status}`}>{query.data.status}</div>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(query.data, null, 2)}</pre>
        </>
      )}
      {query.error && <div className="muted">Не удалось получить статус</div>}
    </GlassCard>
  );
};

export default JobDetailsPage;
