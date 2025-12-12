import { useMemo, type CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { getConfig, getHealthDetailed } from "../../services/api/config";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";
import SectionHeader from "../../components/common/SectionHeader";

type Tone = "positive" | "warning" | "danger";

const DashboardPage = () => {
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: getHealthDetailed });

  const llmLabel = useMemo(() => {
    if (config === undefined) return "Pending";
    return config.llm_available ? "OK" : "No";
  }, [config]);

  const computeLabel = useMemo(() => {
    if (config === undefined) return "Pending";
    return config.compute_available ? "OK" : "No";
  }, [config]);

  const gitlabLabel = useMemo(() => {
    if (config === undefined) return "Pending";
    return config.gitlab_configured ? "OK" : "Pending";
  }, [config]);

  const llmStatus = useMemo<Tone>(() => {
    if (config === undefined) return "warning";
    return config.llm_available ? "positive" : "danger";
  }, [config]);

  const computeStatus = useMemo<Tone>(() => {
    if (config === undefined) return "warning";
    return config.compute_available ? "positive" : "danger";
  }, [config]);

  const gitlabStatus = useMemo<Tone>(() => {
    if (config === undefined) return "warning";
    return config.gitlab_configured ? "positive" : "warning";
  }, [config]);

  return (
    <div className="grid" style={{ gap: 20 }}>
      <GlassCard
        glow
        padding="26px"
        style={{
          position: "relative",
          overflow: "hidden",
          background:
            "linear-gradient(135deg, rgba(12,19,36,0.95), rgba(6,10,22,0.88))",
          boxShadow:
            "0 32px 120px rgba(0,0,0,0.7), 0 0 0 1px rgba(34,211,238,0.12), inset 0 1px 0 rgba(255,255,255,0.04)",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: "-20% -40% auto auto",
            background: "radial-gradient(520px at 70% 20%, rgba(34,211,238,0.26), transparent 60%)",
            filter: "blur(20px)",
            opacity: 0.9,
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.05fr 0.95fr",
            gap: 28,
            alignItems: "center",
            position: "relative",
            zIndex: 1,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <span className="tag" style={{ width: "fit-content", background: "rgba(255,255,255,0.07)" }}>
              Premium dark mode · Glassmorphism
            </span>
            <h1
              style={{
                margin: 0,
                fontSize: "52px",
                lineHeight: 1.03,
                fontWeight: 800,
              }}
            >
              TestOps Copilot — уверенный запуск релизов с LLM‑ассистентом
            </h1>
            <p className="muted" style={{ fontSize: 18, maxWidth: 660, margin: 0 }}>
              Генерация тест-кейсов и автотестов, контроль стандартов и статус инфраструктуры в одном
              тёмном дашборде. Данные обновляются в реальном времени, а критичные сигналы подсвечены акцентом.
            </p>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <GradientButton>Generate tests</GradientButton>
              <GradientButton variant="ghost">Live demo</GradientButton>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 12,
              }}
            >
              <div
                style={{
                  background: "linear-gradient(135deg, rgba(168,85,247,0.25), rgba(34,211,238,0.25))",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 16,
                  padding: "12px 14px",
                  boxShadow: "0 14px 42px rgba(0,0,0,0.45), 0 0 0 1px rgba(168,85,247,0.2)",
                }}
              >
                <div style={{ fontWeight: 700, fontSize: 16 }}>AI сценарии</div>
                <div className="muted" style={{ marginTop: 6 }}>
                  Генерация автотестов под спецификацию и требования.
                </div>
              </div>
              <div
                style={{
                  background: "linear-gradient(135deg, rgba(34,211,238,0.22), rgba(22,163,74,0.18))",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 16,
                  padding: "12px 14px",
                  boxShadow: "0 14px 42px rgba(0,0,0,0.45), 0 0 0 1px rgba(34,211,238,0.18)",
                }}
              >
                <div style={{ fontWeight: 700, fontSize: 16 }}>Контроль дрейфа</div>
                <div className="muted" style={{ marginTop: 6 }}>
                  Мониторинг стабильности, дрейфа требований и покрытия.
                </div>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
                flexWrap: "wrap",
                color: "var(--text-secondary)",
              }}
            >
              <span className="badge-soft" style={{ borderColor: "rgba(255,255,255,0.12)" }}>
                React · Vite · FastAPI · Cloud.ru LLM
              </span>
              <span className="badge-soft" style={{ borderColor: "rgba(34,211,238,0.35)", background: "rgba(34,211,238,0.08)", color: "#b5f3ff" }}>
                Realtime status
              </span>
            </div>
          </div>

          <AnalyticsPreview />
        </div>
      </GlassCard>

      <div className="grid three">
        <KpiCard label="LLM" status={llmLabel} tone={llmStatus} />
        <KpiCard label="Compute" status={computeLabel} tone={computeStatus} />
        <KpiCard label="GitLab" status={gitlabLabel} tone={gitlabStatus} />
      </div>

      <GlassCard
        glow={false}
        style={{
          border: "1px solid rgba(255,255,255,0.08)",
          boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
        }}
      >
        <SectionHeader title="Система" subtitle="Сводка по конфигурации и доступности." />
        {config ? (
          <div className="grid two" style={{ marginTop: 14 }}>
            <ul
              className="muted"
              style={{
                listStyle: "none",
                margin: 0,
                display: "grid",
                gap: 10,
                background: "rgba(255,255,255,0.02)",
                borderRadius: 14,
                border: "1px solid rgba(255,255,255,0.05)",
                padding: 14,
              }}
            >
              <li>LLM модель: {config.llm_model}</li>
              <li>Compute: {config.compute_endpoint}</li>
              <li>GitLab настроен: {config.gitlab_configured ? "да" : "нет"}</li>
            </ul>
            <ul
              className="muted"
              style={{
                listStyle: "none",
                // padding: 0,
                margin: 0,
                display: "grid",
                gap: 10,
                background: "rgba(255,255,255,0.02)",
                borderRadius: 14,
                border: "1px solid rgba(255,255,255,0.05)",
                padding: 14,
              }}
            >
              <li>LLM доступен: {config.llm_available ? "да" : "нет"}</li>
              <li>Compute доступен: {config.compute_available ? "да" : "нет"}</li>
              <li>Окружение: {config.environment}</li>
            </ul>
          </div>
        ) : (
          <div className="muted" style={{ marginTop: 12 }}>
            Загрузка...
          </div>
        )}
      </GlassCard>

      <GlassCard
        glow={false}
        style={{
          border: "1px solid rgba(255,255,255,0.08)",
          boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
        }}
      >
        <SectionHeader title="Health" subtitle="Детальный статус компонентов." />
        <pre className="log-block" style={{ whiteSpace: "pre-wrap", marginTop: 12 }}>
{JSON.stringify(health, null, 2)}
        </pre>
      </GlassCard>
    </div>
  );
};

const tonePalette: Record<Tone, { hex: string; rgb: string }> = {
  positive: { hex: "#22c55e", rgb: "34,197,94" },
  warning: { hex: "#fbbf24", rgb: "251,191,36" },
  danger: { hex: "#ef4444", rgb: "239,68,68" },
};

const KpiCard = ({ label, status, tone }: { label: string; status: string; tone: Tone }) => {
  const palette = tonePalette[tone];
  return (
    <GlassCard
      glow={false}
      className="kpiTile"
      style={
        {
          borderColor: `rgba(${palette.rgb}, 0.45)`,
          boxShadow: `0 16px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(${palette.rgb}, 0.32)`,
          ["--tone-rgb" as any]: palette.rgb,
        } as CSSProperties
      }
    >
      <div className="kpiLabel">{label}</div>
      <div className="kpiValue" style={{ color: palette.hex, marginTop: 6 }}>
        {status}
      </div>
      <div className="muted-dim" style={{ fontSize: 12, marginTop: 6 }}>
        Обновлено в реальном времени
      </div>
    </GlassCard>
  );
};

const AnalyticsPreview = () => {
  const chartPath =
    "M0 110 L40 86 L80 94 L120 70 L160 74 L200 58 L240 62 L280 46 L320 52";
  const areaPath = `${chartPath} L320 150 L0 150 Z`;

  return (
    <div style={{ position: "relative" }}>
      <div
        style={{
          position: "absolute",
          inset: "-80px -60px auto auto",
          background: "radial-gradient(360px at 70% 40%, rgba(168,85,247,0.4), transparent 60%)",
          filter: "blur(24px)",
          opacity: 0.85,
          pointerEvents: "none",
        }}
      />
      <GlassCard
        glow
        padding="18px"
        style={{
          background: "linear-gradient(150deg, rgba(16,26,46,0.92), rgba(8,12,24,0.88))",
          border: "1px solid rgba(255,255,255,0.12)",
          boxShadow: "0 28px 110px rgba(0,0,0,0.7), 0 0 0 1px rgba(34,211,238,0.16)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
          <div>
            <div className="muted-dim" style={{ textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 12 }}>
              analytics preview
            </div>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4 }}>Release readiness</div>
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              Последние 10 прогонов CI
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span className="badge-soft" style={{ borderColor: "rgba(34,211,238,0.35)", background: "rgba(34,211,238,0.12)", color: "#a5f3fc" }}>
              Stable
            </span>
            <span className="badge-soft" style={{ borderColor: "rgba(168,85,247,0.35)", background: "rgba(168,85,247,0.14)", color: "#d8b4fe" }}>
              LLM assist
            </span>
          </div>
        </div>

        <div
          style={{
            marginTop: 14,
            borderRadius: 14,
            padding: 12,
            background:
              "radial-gradient(260px at 18% 30%, rgba(255,255,255,0.05), transparent 60%), rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <svg viewBox="0 0 320 160" role="img" aria-label="Release readiness chart" style={{ width: "100%", height: "150px" }}>
            <defs>
              <linearGradient id="line" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#a855f7" />
                <stop offset="100%" stopColor="#22d3ee" />
              </linearGradient>
              <linearGradient id="area" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="rgba(168,85,247,0.32)" />
                <stop offset="100%" stopColor="rgba(34,211,238,0.05)" />
              </linearGradient>
            </defs>
            <path d={areaPath} fill="url(#area)" opacity="0.9" />
            <path d={chartPath} fill="none" stroke="url(#line)" strokeWidth="3.2" strokeLinecap="round" />
            {[0, 40, 80, 120, 160, 200, 240, 280, 320].map((x, idx) => {
              const yPositions = [110, 86, 94, 70, 74, 58, 62, 46, 52];
              return (
                <circle
                  key={x}
                  cx={x}
                  cy={yPositions[idx]}
                  r={4.2}
                  fill="#0b1224"
                  stroke="#22d3ee"
                  strokeWidth="1.8"
                  opacity={0.95}
                />
              );
            })}
          </svg>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12, marginTop: 12 }}>
          <div>
            <div className="muted-dim" style={{ fontSize: 12 }}>Покрытие регрессии</div>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>92%</div>
            <div className="muted" style={{ fontSize: 12 }}>+3% за неделю</div>
          </div>
          <div>
            <div className="muted-dim" style={{ fontSize: 12 }}>AI сгенерировано</div>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>128 сценариев</div>
            <div className="muted" style={{ fontSize: 12 }}>drift alerts: 2</div>
          </div>
          <div>
            <div className="muted-dim" style={{ fontSize: 12 }}>Стабильность</div>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4, color: "#22c55e" }}>99.4%</div>
            <div className="muted" style={{ fontSize: 12 }}>CI flakiness ↓</div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};

export default DashboardPage;
