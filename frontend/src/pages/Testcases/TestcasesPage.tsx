import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  generateManualUI,
  generateManualAPI,
  getTestcaseJob,
  downloadTestcases,
} from "../../services/api/testcases";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

const blocks = ["main_page", "product_catalog", "configuration", "management", "mobile"];
const sections = ["vms", "disks", "flavors", "other"];

const TestcasesPage = () => {
  const [activeTab, setActiveTab] = useState<"ui" | "api">("ui");
  const [uiJobId, setUiJobId] = useState<string | null>(null);
  const [apiJobId, setApiJobId] = useState<string | null>(null);

  const uiMutation = useMutation({
    mutationFn: generateManualUI,
    onSuccess: (res) => setUiJobId(res.job_id),
  });

  const apiMutation = useMutation({
    mutationFn: generateManualAPI,
    onSuccess: (res) => setApiJobId(res.job_id),
  });

  const { job: uiJob } = useJobWatcher(uiJobId, getTestcaseJob);
  const { job: apiJob } = useJobWatcher(apiJobId, getTestcaseJob);

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard
        padding="22px"
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Генерация тест-кейсов</div>
            <div className="panelHint">Одним кликом — UI или API сценарии, готовые к скачиванию.</div>
            <div className="chipRow tight">
              <span className="pillSoft">LLM assist</span>
              <span className="pillSoft">Spec → Steps → Cases</span>
              <span className="pillSoft">Validation hints</span>
            </div>
          </div>
          <div className="pillTabs">
            <button className={`pill ${activeTab === "ui" ? "active" : ""}`} type="button" onClick={() => setActiveTab("ui")}>
              UI калькулятор
            </button>
            <button className={`pill ${activeTab === "api" ? "active" : ""}`} type="button" onClick={() => setActiveTab("api")}>
              API (OpenAPI)
            </button>
          </div>
        </div>
        <div className="divider" style={{ margin: "16px 0" }} />
        <div className="grid two" style={{ gap: 16 }}>
          <GlassCard glow={false}>
            {activeTab === "ui" ? (
              <UiForm onSubmit={(data) => uiMutation.mutate(data)} loading={uiMutation.isPending} />
            ) : (
              <ApiForm onSubmit={(data) => apiMutation.mutate(data)} loading={apiMutation.isPending} />
            )}
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Шаги и критерии</div>
            <div className="panelHint">Быстрая сверка перед генерацией.</div>
            <div className="stack" style={{ marginTop: 10 }}>
              <div className="metricRow">
                <span className="metricLabel">Шаг 1</span>
                <span className="metricValue">Опишите требования</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Шаг 2</span>
                <span className="metricValue">Выберите блоки/секции</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Шаг 3</span>
                <span className="metricValue">Задайте объём и приоритет</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Готово</span>
                <span className="metricValue">Запустите генерацию</span>
              </div>
            </div>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Советы</div>
            <ul className="muted" style={{ margin: "6px 0 0", paddingLeft: 16, display: "grid", gap: 6 }}>
              <li>Делите требования на краткие пункты — выше точность.</li>
              <li>Снимаете галки блоков — сокращаете объём.</li>
              <li>Для API используйте конкретный OpenAPI URL.</li>
            </ul>
          </GlassCard>
        </div>
      </GlassCard>

      <div className="grid two" style={{ gap: 16 }}>
        <JobPanel
          title="UI кейсы"
          job={uiJob}
          onDownload={() =>
            uiJobId && downloadTestcases(uiJobId).then((b) => downloadBlob(b, "ui_testcases.zip"))
          }
        />
        <JobPanel
          title="API кейсы"
          job={apiJob}
          onDownload={() =>
            apiJobId && downloadTestcases(apiJobId).then((b) => downloadBlob(b, "api_testcases.zip"))
          }
        />
      </div>
    </div>
  );
};

type UiFormProps = {
  onSubmit: (data: any) => void;
  loading: boolean;
};

const UiForm = ({ onSubmit, loading }: UiFormProps) => {
  const [requirements, setReq] = useState("");
  const [selectedBlocks, setSelectedBlocks] = useState<string[]>(blocks);
  const [count, setCount] = useState(25);
  const [priority, setPriority] = useState("CRITICAL");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          requirements,
          test_blocks: selectedBlocks,
          target_count: count,
          priority,
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard">
          <div className="fieldLabel">Требования</div>
          <textarea
            className="textarea"
            value={requirements}
            onChange={(e) => setReq(e.target.value)}
            required
            placeholder="Опишите цели, сценарии, крайние случаи..."
            style={{ minHeight: 150 }}
          />
        </div>
        <div className="subCard" style={{ display: "grid", gap: 12 }}>
          <div>
            <div className="fieldLabel">Блоки</div>
            <div className="chipRow">
              {blocks.map((b) => (
                <label key={b} className="chip">
                  <input
                    type="checkbox"
                    checked={selectedBlocks.includes(b)}
                    onChange={() =>
                      setSelectedBlocks((prev) =>
                        prev.includes(b) ? prev.filter((x) => x !== b) : [...prev, b],
                      )
                    }
                  />
                  {b}
                </label>
              ))}
            </div>
          </div>
          <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
            <div>
              <div className="fieldLabel">Количество</div>
              <input
                className="input"
                type="number"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                min={1}
                max={100}
              />
            </div>
            <div>
              <div className="fieldLabel">Приоритет</div>
              <select className="select" value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="CRITICAL">CRITICAL</option>
                <option value="NORMAL">NORMAL</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать UI кейсы"}
      </GradientButton>
    </form>
  );
};

const ApiForm = ({
  onSubmit,
  loading,
}: {
  onSubmit: (data: any) => void;
  loading: boolean;
}) => {
  const [openapiUrl, setUrl] = useState("https://compute.api.cloud.ru/openapi.json");
  const [selectedSections, setSections] = useState<string[]>(["vms", "disks", "flavors"]);
  const [count, setCount] = useState(25);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          openapi_url: openapiUrl,
          sections: selectedSections,
          target_count: count,
          auth_type: "bearer",
          priority: "NORMAL",
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard" style={{ display: "grid", gap: 12 }}>
          <div>
            <div className="fieldLabel">OpenAPI URL</div>
            <input className="input" value={openapiUrl} onChange={(e) => setUrl(e.target.value)} required />
          </div>
          <div>
            <div className="fieldLabel">Количество</div>
            <input
              className="input"
              type="number"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              min={1}
              max={100}
            />
          </div>
        </div>
        <div className="subCard">
          <div className="fieldLabel">Секции</div>
          <div className="chipRow">
            {sections.map((s) => (
              <label key={s} className="chip">
                <input
                  type="checkbox"
                  checked={selectedSections.includes(s)}
                  onChange={() =>
                    setSections((prev) =>
                      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s],
                    )
                  }
                />
                {s}
              </label>
            ))}
          </div>
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать API кейсы"}
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
      {job.testcases?.length ? (
        <>
          <div className="muted" style={{ marginTop: 8 }}>Получено кейсов: {job.testcases.length}</div>
          <table className="table" style={{ marginTop: 8 }}>
            <thead>
              <tr>
                <th>Title</th>
                <th>Feature</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {job.testcases.slice(0, 5).map((tc: any) => (
                <tr key={tc.id}>
                  <td>{tc.title}</td>
                  <td>{tc.feature}</td>
                  <td>{tc.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <div className="muted" style={{ marginTop: 8 }}>Результаты появятся после завершения задачи.</div>
      )}
      {job.status === "completed" && (
        <GradientButton variant="ghost" onClick={onDownload} style={{ marginTop: 10 }}>
          Скачать zip
        </GradientButton>
      )}
    </GlassCard>
  );
};

export default TestcasesPage;

