import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  generateUIAutotests,
  generateAPIAutotests,
  getAutotestJob,
  downloadAutotests,
} from "../../services/api/autotests";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

const AutotestsPage = () => {
  const [activeTab, setActiveTab] = useState<"ui" | "api">("ui");
  const [uiJobId, setUiJobId] = useState<string | null>(null);
  const [apiJobId, setApiJobId] = useState<string | null>(null);

  const uiMutation = useMutation({
    mutationFn: generateUIAutotests,
    onSuccess: (res) => setUiJobId(res.job_id),
  });

  const apiMutation = useMutation({
    mutationFn: generateAPIAutotests,
    onSuccess: (res) => setApiJobId(res.job_id),
  });

  const { job: uiJob } = useJobWatcher(uiJobId, getAutotestJob);
  const { job: apiJob } = useJobWatcher(apiJobId, getAutotestJob);

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard
        padding="22px"
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Генерация автотестов</div>
            <div className="panelHint">UI e2e (Playwright) и API (pytest/httpx) в одном месте.</div>
            <div className="chipRow tight">
              <span className="pillSoft">Headless ready</span>
              <span className="pillSoft">Priority filter</span>
              <span className="pillSoft">LLM prompts tuned</span>
            </div>
          </div>
          <div className="pillTabs">
            <button className={`pill ${activeTab === "ui" ? "active" : ""}`} type="button" onClick={() => setActiveTab("ui")}>
              UI e2e
            </button>
            <button className={`pill ${activeTab === "api" ? "active" : ""}`} type="button" onClick={() => setActiveTab("api")}>
              API
            </button>
          </div>
        </div>
        <div className="divider" style={{ margin: "16px 0" }} />
        <div className="grid two" style={{ gap: 16 }}>
          <GlassCard glow={false}>
            {activeTab === "ui" ? (
              <UiAutotestForm onSubmit={(d) => uiMutation.mutate(d)} loading={uiMutation.isPending} />
            ) : (
              <ApiAutotestForm onSubmit={(d) => apiMutation.mutate(d)} loading={apiMutation.isPending} />
            )}
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Тактика генерации</div>
            <div className="panelHint">Минимум шагов — максимум готовности.</div>
            <div className="stack" style={{ marginTop: 10 }}>
              <div className="metricRow">
                <span className="metricLabel">UI</span>
                <span className="metricValue">IDs + base URL + browsers</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">API</span>
                <span className="metricValue">IDs + OpenAPI + sections</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Выход</span>
                <span className="metricValue">Zip с готовыми тестами</span>
              </div>
            </div>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Советы</div>
            <ul className="muted" style={{ margin: "6px 0 0", paddingLeft: 16, display: "grid", gap: 6 }}>
              <li>UI: передавайте ID только критичных кейсов.</li>
              <li>API: уточняйте секции через запятую.</li>
              <li>Token опционален — но ускоряет доступ к приватке.</li>
            </ul>
          </GlassCard>
        </div>
      </GlassCard>

      <div className="grid two" style={{ gap: 16 }}>
        <JobPanel
          title="UI автотесты"
          job={uiJob}
          onDownload={() =>
            uiJobId && downloadAutotests(uiJobId).then((b) => downloadBlob(b, "ui_autotests.zip"))
          }
        />
        <JobPanel
          title="API автотесты"
          job={apiJob}
          onDownload={() =>
            apiJobId && downloadAutotests(apiJobId).then((b) => downloadBlob(b, "api_autotests.zip"))
          }
        />
      </div>
    </div>
  );
};

const UiAutotestForm = ({ onSubmit, loading }: { onSubmit: (d: any) => void; loading: boolean }) => {
  const [ids, setIds] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://cloud.ru/calculator");
  const [browsers, setBrowsers] = useState("chromium");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          manual_testcases_ids: ids.split(",").map((s) => s.trim()).filter(Boolean),
          framework: "playwright",
          browsers: browsers.split(",").map((s) => s.trim()).filter(Boolean),
          base_url: baseUrl,
          headless: true,
          priority_filter: ["CRITICAL", "NORMAL"],
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">UUID ручных кейсов (через запятую)</div>
          <input className="input" value={ids} onChange={(e) => setIds(e.target.value)} required placeholder="uuid-1, uuid-2, uuid-3" />
        </div>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">Браузеры</div>
          <input className="input" value={browsers} onChange={(e) => setBrowsers(e.target.value)} placeholder="chromium,webkit" />
          <div className="fieldLabel" style={{ marginTop: 6 }}>Base URL</div>
          <input className="input" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать UI автотесты"}
      </GradientButton>
    </form>
  );
};

const ApiAutotestForm = ({ onSubmit, loading }: { onSubmit: (d: any) => void; loading: boolean }) => {
  const [ids, setIds] = useState("");
  const [openapiUrl, setUrl] = useState("https://compute.api.cloud.ru/openapi.json");
  const [sections, setSections] = useState("vms,disks,flavors");
  const [token, setToken] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          manual_testcases_ids: ids.split(",").map((s) => s.trim()).filter(Boolean),
          openapi_url: openapiUrl,
          sections: sections.split(",").map((s) => s.trim()).filter(Boolean),
          base_url: "https://compute.api.cloud.ru",
          auth_token: token || null,
          test_framework: "pytest",
          http_client: "httpx",
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">UUID ручных кейсов (через запятую)</div>
          <input className="input" value={ids} onChange={(e) => setIds(e.target.value)} required />
          <div className="subLabel">Только завершённые кейсы попадут в отбор.</div>
        </div>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">OpenAPI URL</div>
          <input className="input" value={openapiUrl} onChange={(e) => setUrl(e.target.value)} required />
          <div className="fieldLabel">Секции</div>
          <input className="input" value={sections} onChange={(e) => setSections(e.target.value)} placeholder="vms,disks,flavors" />
          <div className="fieldLabel">Bearer token</div>
          <input className="input" value={token} onChange={(e) => setToken(e.target.value)} placeholder="опционально" />
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать API автотесты"}
      </GradientButton>
    </form>
  );
};

const JobPanel = ({
  title,
  job,
  onDownload,
}: {
  title: string;
  job: any;
  onDownload: () => void;
}) => {
  if (!job) return null;
  return (
    <GlassCard
      glow={false}
      style={{
        border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 18px 50px rgba(0,0,0,0.5)",
      }}
    >
      <div className="section-title" style={{ alignItems: "center", gap: 10 }}>
        {title}
        <span className={`pillBadge status ${job.status}`} style={{ textTransform: "uppercase" }}>
          {job.status}
        </span>
      </div>
      <div className="muted" style={{ marginTop: 4, fontSize: 13 }}>Job ID: {job.job_id}</div>
      {job.status === "completed" && (
        <GradientButton variant="ghost" onClick={onDownload} style={{ marginTop: 10 }}>
          Скачать zip
        </GradientButton>
      )}
    </GlassCard>
  );
};

export default AutotestsPage;

