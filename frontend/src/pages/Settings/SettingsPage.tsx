import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { getConfig, validateCompute, validateGitlab, validateLLM } from "../../services/api/config";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

const SettingsPage = () => {
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });

  const computeMutation = useMutation({ mutationFn: validateCompute });
  const gitlabMutation = useMutation({ mutationFn: validateGitlab });
  const llmMutation = useMutation({ mutationFn: validateLLM });

  const [computeToken, setComputeToken] = useState("");
  const [gitlabToken, setGitlabToken] = useState("");
  const [gitlabProject, setGitlabProject] = useState("");
  const [llmKey, setLlmKey] = useState("");

  const palette = {
    positive: { badge: "pillBadge positive", label: "OK" },
    warning: { badge: "pillBadge warning", label: "Pending" },
    danger: { badge: "pillBadge danger", label: "No" },
  };

  const availability = [
    {
      title: "LLM",
      ok: config?.llm_available,
      detail: config?.llm_model ? `Модель: ${config.llm_model}` : "LLM endpoint",
    },
    {
      title: "Compute",
      ok: config?.compute_available,
      detail: config?.compute_endpoint ? `Endpoint: ${config.compute_endpoint}` : "Compute endpoint",
    },
    {
      title: "GitLab",
      ok: config?.gitlab_configured,
      detail: config?.environment ? `Env: ${config.environment}` : "PAT / Project ID",
    },
  ];

  return (
    <div className="grid" style={{ gap: 16 }}>
      <GlassCard
        padding="22px"
        style={{
          background: "linear-gradient(135deg, rgba(12,19,36,0.94), rgba(6,10,22,0.9))",
          boxShadow: "0 32px 120px rgba(0,0,0,0.7), 0 0 0 1px rgba(168,85,247,0.14)",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Подключения и проверки</div>
            <div className="panelHint">LLM, Compute, GitLab — быстро проверить и сохранить токены.</div>
            <div className="chipRow tight">
              <span className="pillSoft">Live validation</span>
              <span className="pillSoft">Обновление статуса</span>
            </div>
          </div>
          <span className="pillBadge" style={{ borderColor: "rgba(255,255,255,0.12)" }}>Control center</span>
        </div>
      </GlassCard>

      <div className="grid three" style={{ gap: 12 }}>
        {availability.map((item) => {
          const tone = item.ok === undefined ? "warning" : item.ok ? "positive" : "danger";
          const toneCfg = palette[tone as keyof typeof palette];
          return (
            <GlassCard
              key={item.title}
              glow={false}
              className="kpiTile"
              style={{
                borderColor:
                  tone === "positive"
                    ? "rgba(34,197,94,0.35)"
                    : tone === "warning"
                    ? "rgba(251,191,36,0.35)"
                    : "rgba(239,68,68,0.35)",
                boxShadow: "0 14px 38px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                <div className="kpiLabel" style={{ color: "var(--text-secondary)" }}>{item.title}</div>
                <span className={toneCfg.badge}>{toneCfg.label}</span>
              </div>
              <div className="kpiValue" style={{ marginTop: 4, color: "#f9fafb", fontSize: 22 }}>
                {item.ok === undefined ? "—" : item.ok ? "Доступно" : "Недоступно"}
              </div>
              <div className="muted-dim" style={{ marginTop: 4, fontSize: 12 }}>{item.detail}</div>
            </GlassCard>
          );
        })}
      </div>

      <div className="grid two" style={{ gap: 16 }}>
      <GlassCard
        padding="20px"
        style={{
          background: "linear-gradient(135deg, rgba(12,19,36,0.9), rgba(8,12,24,0.86))",
          boxShadow: "0 18px 70px rgba(0,0,0,0.6), 0 0 0 1px rgba(168,85,247,0.12)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div>
            <div className="panelTitle">LLM</div>
            <div className="panelHint">Проверка доступа к Cloud.ru LLM.</div>
          </div>
          <span className="pillBadge warning">Token</span>
        </div>
        <input
          className="input"
          placeholder="API key"
          value={llmKey}
          onChange={(e) => setLlmKey(e.target.value)}
          style={{ marginTop: 10 }}
        />
        <GradientButton
          style={{ marginTop: 10 }}
          onClick={() => llmMutation.mutate({ api_key: llmKey })}
          disabled={llmMutation.isPending}
        >
          {llmMutation.isPending ? "Проверка..." : "Проверить LLM"}
        </GradientButton>
        {llmMutation.data && <pre className="log-block" style={{ marginTop: 12 }}>{JSON.stringify(llmMutation.data, null, 2)}</pre>}
      </GlassCard>

      <GlassCard
        padding="20px"
        style={{
          background: "linear-gradient(135deg, rgba(12,19,36,0.9), rgba(8,12,24,0.86))",
          boxShadow: "0 18px 70px rgba(0,0,0,0.6), 0 0 0 1px rgba(34,211,238,0.12)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div>
            <div className="panelTitle">Compute API</div>
            <div className="panelHint">Валидация токена доступа.</div>
          </div>
          <span className="pillBadge warning">Bearer</span>
        </div>
        <input
          className="input"
          placeholder="Bearer token / key"
          value={computeToken}
          onChange={(e) => setComputeToken(e.target.value)}
          style={{ marginTop: 10 }}
        />
        <GradientButton
          style={{ marginTop: 10 }}
          onClick={() => computeMutation.mutate({ token: computeToken })}
          disabled={computeMutation.isPending}
        >
          {computeMutation.isPending ? "Проверка..." : "Проверить Compute"}
        </GradientButton>
        {computeMutation.data && <pre className="log-block" style={{ marginTop: 12 }}>{JSON.stringify(computeMutation.data, null, 2)}</pre>}
      </GlassCard>

      <GlassCard
        padding="20px"
        style={{
          background: "linear-gradient(135deg, rgba(12,19,36,0.9), rgba(8,12,24,0.86))",
          boxShadow: "0 18px 70px rgba(0,0,0,0.6), 0 0 0 1px rgba(168,85,247,0.12)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div>
            <div className="panelTitle">GitLab</div>
            <div className="panelHint">Проверьте PAT и проект.</div>
          </div>
          <span className="pillBadge warning">PAT</span>
        </div>
        <input
          className="input"
          placeholder="GitLab token"
          value={gitlabToken}
          onChange={(e) => setGitlabToken(e.target.value)}
          style={{ marginTop: 10 }}
        />
        <input
          className="input"
          style={{ marginTop: 8 }}
          placeholder="Project ID"
          value={gitlabProject}
          onChange={(e) => setGitlabProject(e.target.value)}
        />
        <GradientButton
          style={{ marginTop: 10 }}
          onClick={() => gitlabMutation.mutate({ token: gitlabToken, project_id: gitlabProject })}
          disabled={gitlabMutation.isPending}
        >
          {gitlabMutation.isPending ? "Проверка..." : "Проверить GitLab"}
        </GradientButton>
        {gitlabMutation.data && <pre className="log-block" style={{ marginTop: 12 }}>{JSON.stringify(gitlabMutation.data, null, 2)}</pre>}
      </GlassCard>

      <GlassCard
        padding="20px"
        style={{
          background: "linear-gradient(135deg, rgba(12,19,36,0.9), rgba(8,12,24,0.86))",
          boxShadow: "0 18px 70px rgba(0,0,0,0.6), 0 0 0 1px rgba(34,211,238,0.12)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div className="panelTitle">Текущее состояние</div>
          <span className="pillBadge" style={{ borderColor: "rgba(255,255,255,0.12)" }}>Snapshot</span>
        </div>
        {config ? (
          <pre className="log-block" style={{ marginTop: 10 }}>{JSON.stringify(config, null, 2)}</pre>
        ) : (
          <div className="muted" style={{ marginTop: 10 }}>Загрузка...</div>
        )}
      </GlassCard>
      </div>
    </div>
  );
};

export default SettingsPage;

