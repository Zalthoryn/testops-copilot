import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { checkStandards, getStandardsJob, downloadStandardsReport } from "../../services/api/standards";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

const availableChecks = ["aaa", "allure", "naming", "documentation", "structure"];

const StandardsPage = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [checks, setChecks] = useState<string[]>(["aaa", "allure", "naming"]);
  const [jobId, setJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const mutation = useMutation({
    mutationFn: () => checkStandards(files, checks),
    onSuccess: (res) => setJobId(res.job_id),
  });

  const { job } = useJobWatcher(jobId, getStandardsJob);

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard
        padding="22px"
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Проверка стандартов</div>
            <div className="panelHint">AAA, Allure, naming, structure. Загрузи файлы — получи отчёт.</div>
            <div className="chipRow tight">
              <span className="pillSoft">Паттерны</span>
              <span className="pillSoft">Документация</span>
              <span className="pillSoft">CI report</span>
            </div>
          </div>
          <span className="badge-soft" style={{ borderColor: "rgba(168,85,247,0.28)", background: "rgba(168,85,247,0.12)", color: "#e9d5ff" }}>
            LLM-assisted review
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
              <div className="subCard" style={{ display: "grid", gap: 10 }}>
                <div className="fieldLabel">Файлы</div>
                <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={(e) => setFiles(Array.from(e.target.files || []))}
                    style={{ display: "none" }}
                  />
                  <button
                    type="button"
                    className="pillSoft"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Выбрать файлы
                  </button>
                  <span className="muted">
                    {files.length
                      ? files.slice(0, 2).map((f) => f.name).join(", ") + (files.length > 2 ? ` и еще ${files.length - 2}` : "")
                      : "Файл не выбран"}
                  </span>
                </div>
                <div className="subLabel">Можно загрузить несколько файлов одновременно.</div>
              </div>

              <div className="subCard" style={{ display: "grid", gap: 10 }}>
                <div className="fieldLabel">Проверки</div>
                <div className="chipRow">
                  {availableChecks.map((c) => (
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
                {mutation.isPending ? "Проверка..." : "Запустить проверку"}
              </GradientButton>
            </form>
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Справка</div>
            <div className="panelHint">Что влияет на результаты.</div>
            <ul className="muted" style={{ marginTop: 10, paddingLeft: 16, display: "grid", gap: 6 }}>
              <li>AAA: сигнатуры тестов, понятные шаги, без дублирующих assert.</li>
              <li>Allure: аннотации, теги, привязка к story/feature.</li>
              <li>Naming: консистентность названий файлов и тестов.</li>
              <li>Structure: дерево каталогов и фикстуры.</li>
            </ul>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Формат отчёта</div>
            <div className="muted" style={{ marginTop: 6 }}>
              HTML-отчёт с деталями по каждому чекеру, статусами и рекомендациями. Доступен после завершения job.
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
                downloadStandardsReport(jobId).then((blob) => downloadBlob(blob, "standards_report.html"))
              }
              style={{ marginTop: 10 }}
            >
              Скачать отчёт
            </GradientButton>
          )}
        </GlassCard>
      )}
    </div>
  );
};

export default StandardsPage;

