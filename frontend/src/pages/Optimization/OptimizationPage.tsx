import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { analyzeOptimization, getOptimizationJob, downloadOptimized } from "../../services/api/optimization";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

const OptimizationPage = () => {
  const [repo, setRepo] = useState("");
  const [requirements, setRequirements] = useState("");
  const [checks, setChecks] = useState<string[]>(["duplicates", "coverage", "outdated"]);
  const [jobId, setJobId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      analyzeOptimization({
        repository_url: repo || null,
        requirements: requirements || null,
        checks,
        optimization_level: "moderate",
      }),
    onSuccess: (res) => setJobId(res.job_id),
  });

  const { job } = useJobWatcher(jobId, getOptimizationJob);

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard
        padding="22px"
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Оптимизация тестов</div>
            <div className="panelHint">Поиск дублей, coverage и устаревших кейсов. Настрой фильтры и получи zip.</div>
            <div className="chipRow tight">
              <span className="pillSoft">Duplicates</span>
              <span className="pillSoft">Coverage</span>
              <span className="pillSoft">Outdated</span>
            </div>
          </div>
          <span className="badge-soft" style={{ borderColor: "rgba(34,211,238,0.3)", background: "rgba(34,211,238,0.1)", color: "#a5f3fc" }}>
            Drift & coverage
          </span>
        </div>

        <div className="grid two" style={{ gap: 16, marginTop: 14 }}>
          <GlassCard glow={false}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                mutation.mutate();
              }}
              className="stack"
            >
              <div className="grid two" style={{ gap: 12 }}>
                <div className="subCard" style={{ display: "grid", gap: 8 }}>
                  <div className="fieldLabel">Repo URL (опционально)</div>
                  <input className="input" value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="https://gitlab.com/your/repo" />
                  <div className="subLabel">Если пусто, анализируется локальный контекст.</div>
                </div>
                <div className="subCard" style={{ display: "grid", gap: 8 }}>
                  <div className="fieldLabel">Требования (опционально)</div>
                  <textarea
                    className="textarea"
                    value={requirements}
                    onChange={(e) => setRequirements(e.target.value)}
                    placeholder="Критерии оптимизации, риски, области покрытия..."
                    style={{ minHeight: 120 }}
                  />
                </div>
              </div>

              <div className="subCard" style={{ display: "grid", gap: 10 }}>
                <div className="fieldLabel">Проверки</div>
                <div className="chipRow">
                  {["duplicates", "coverage", "outdated"].map((c) => (
                    <label key={c} className="chip">
                      <input
                        type="checkbox"
                        checked={checks.includes(c)}
                        onChange={() =>
                          setChecks((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]))
                        }
                      />
                      {c}
                    </label>
                  ))}
                </div>
              </div>

              <GradientButton type="submit" disabled={mutation.isPending} style={{ marginTop: 4 }}>
                {mutation.isPending ? "Анализ..." : "Запустить анализ"}
              </GradientButton>
            </form>
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Гид по улучшению</div>
            <div className="panelHint">На что смотреть в отчёте.</div>
            <div className="stack" style={{ marginTop: 10 }}>
              <div className="metricRow">
                <span className="metricLabel">Duplicates</span>
                <span className="metricValue">Сократить до уникальных</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Coverage</span>
                <span className="metricValue">Заполнить критичные пробелы</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Outdated</span>
                <span className="metricValue">Удалить или переписать</span>
              </div>
            </div>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Результат</div>
            <div className="muted" style={{ marginTop: 6 }}>
              Zip с рекомендациями и метаданными. Каждая группа снабжена ссылками на строки/файлы, где найдено расхождение.
            </div>
          </GlassCard>
        </div>
      </GlassCard>

      {job && (
        <GlassCard
          glow={false}
          style={{
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 18px 50px rgba(0,0,0,0.5)",
          }}
        >
          <div className="section-title" style={{ alignItems: "center", gap: 10 }}>
            Job
            <span className={`pillBadge status ${job.status}`} style={{ textTransform: "uppercase" }}>
              {job.status}
            </span>
          </div>
          <div className="muted" style={{ marginTop: 4, fontSize: 13 }}>Job ID: {job.job_id}</div>
          {job.status === "completed" && (
            <GradientButton
              variant="ghost"
              onClick={() =>
                jobId &&
                downloadOptimized(jobId).then((blob) => downloadBlob(blob, "optimized_tests.zip"))
              }
              style={{ marginTop: 10 }}
            >
              Скачать zip
            </GradientButton>
          )}
        </GlassCard>
      )}
    </div>
  );
};

export default OptimizationPage;

