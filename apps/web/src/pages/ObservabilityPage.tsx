import { useCallback, useEffect, useMemo, useState } from "react";
import pedrocoreLogo from "../assets/pedrocore-logo-icon.png";
import {
  getExecutionDetail,
  getExecutions,
  getObservabilityStatus,
  runGeminiSmoke,
  type ExecutionDetail,
  type ExecutionFilters,
  type ExecutionSummary,
  type ObservabilityStatus,
  type GeminiSmokeResponse,
} from "../services/api";

const EMPTY_FILTERS: ExecutionFilters = {
  origin: "",
  task: "",
  status: "",
  provider: "",
  fallback: "",
};

const REPORT_TASKS = new Set([
  "qa_report_analysis",
  "qa_failure_diagnosis",
  "release_gate_review",
  "exploratory_test_plan",
  "manual_exploration_report",
  "assisted_exploration_review",
  "report_ingestion",
]);

function formatTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(date);
}

function formatJson(value: unknown) {
  if (value == null) return "Não disponível nesta execução.";
  return JSON.stringify(value, null, 2);
}

function statusTone(status: string) {
  if (["ok", "passed", "pass"].includes(status)) return "success";
  if (["blocked", "disabled"].includes(status)) return "warning";
  if (["error", "failed", "fail"].includes(status)) return "danger";
  return "neutral";
}

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="obs-detail-card">
      <h3>{title}</h3>
      <pre>{formatJson(value)}</pre>
    </section>
  );
}

export function ObservabilityPage() {
  const [status, setStatus] = useState<ObservabilityStatus | null>(null);
  const [filters, setFilters] = useState<ExecutionFilters>(EMPTY_FILTERS);
  const [items, setItems] = useState<ExecutionSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ExecutionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [geminiChecks, setGeminiChecks] = useState({ network: false, cost: false, keyIntegrity: false });
  const [geminiRunning, setGeminiRunning] = useState(false);
  const [geminiResult, setGeminiResult] = useState<GeminiSmokeResponse | null>(null);

  const loadExecutions = useCallback(async () => {
    try {
      const nextItems = await getExecutions(filters);
      setItems(nextItems);
      setSelectedId((current) => {
        if (current && nextItems.some((item) => item.execution_id === current)) return current;
        return nextItems[0]?.execution_id ?? null;
      });
      setError("");
    } catch (requestError) {
      setItems([]);
      setSelectedId(null);
      setDetail(null);
      setError(requestError instanceof Error ? requestError.message : "Falha ao carregar execuções.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    getObservabilityStatus()
      .then((nextStatus) => {
        setStatus(nextStatus);
        if (!nextStatus.enabled) {
          setError("Observabilidade desabilitada. Ative PEDROCORE_OBSERVABILITY_ENABLED=true em APP_ENV local/qa/test.");
          setLoading(false);
        }
      })
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "Falha ao consultar observabilidade.");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!status?.enabled) return undefined;
    void loadExecutions();
    const interval = window.setInterval(() => void loadExecutions(), 4_000);
    return () => window.clearInterval(interval);
  }, [loadExecutions, status?.enabled]);

  useEffect(() => {
    if (!selectedId || !status?.enabled) {
      setDetail(null);
      return;
    }
    getExecutionDetail(selectedId)
      .then(setDetail)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Falha no detalhe."));
  }, [selectedId, status?.enabled]);

  const reportCount = useMemo(
    () => items.filter((item) => REPORT_TASKS.has(item.task)).length,
    [items],
  );

  function updateFilter(name: keyof ExecutionFilters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  async function executeGeminiSmoke() {
    setGeminiRunning(true);
    try {
      const result = await runGeminiSmoke(geminiChecks);
      setGeminiResult(result);
      setError("");
      await loadExecutions();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Falha no smoke Gemini.");
    } finally {
      setGeminiRunning(false);
    }
  }

  return (
    <main className="observability-shell">
      <header className="obs-brandbar">
        <div className="obs-brand">
          <img src={pedrocoreLogo} alt="Logo PedroCore IA" />
          <div>
            <strong>PedroCore <span>IA</span></strong>
            <small>Observabilidade técnica</small>
          </div>
        </div>
        <a href="#/">Voltar ao chat</a>
      </header>

      <section className="obs-notice" role="status">
        <div>
          <span className={`obs-live ${status?.enabled ? "active" : ""}`} />
          <strong>MODO DE OBSERVABILIDADE QA/LOCAL</strong>
          <p>Não é painel público. Store volátil, limitado e disponível somente por loopback.</p>
        </div>
        <div className="obs-training-note">
          <strong>Treinamento de modelo: não implementado.</strong>
          <p>Memória técnica não altera os pesos do modelo e não constitui treinamento ou fine-tuning.</p>
        </div>
      </section>

      <section className="obs-summary-grid">
        <article><span>Execuções filtradas</span><strong>{items.length}</strong></article>
        <article><span>Relatórios visíveis</span><strong>{reportCount}</strong></article>
        <article><span>Store</span><strong>{status?.storage ?? "—"}</strong></article>
        <article><span>Limite</span><strong>{status?.max_entries ?? "—"}</strong></article>
      </section>

      <section className="obs-gemini-card" aria-labelledby="gemini-smoke-title">
        <div>
          <span>PROVIDER REAL · OPT-IN DUPLO</span>
          <h2 id="gemini-smoke-title">Smoke Gemini sintético</h2>
          <p>Desativado por padrão. Envia somente “Responda apenas com a palavra OK.”, sem dado financeiro, relatório ou arquivo do usuário.</p>
          <strong>Esta ação faz uma chamada de rede e pode gerar custo. No máximo uma chamada por execução.</strong>
        </div>
        <div className="obs-gemini-controls">
          <label><input type="checkbox" checked={geminiChecks.network} onChange={(event) => setGeminiChecks((current) => ({ ...current, network: event.target.checked }))} /> Confirmo a chamada de rede</label>
          <label><input type="checkbox" checked={geminiChecks.cost} onChange={(event) => setGeminiChecks((current) => ({ ...current, cost: event.target.checked }))} /> Confirmo o possível custo</label>
          <label><input type="checkbox" checked={geminiChecks.keyIntegrity} onChange={(event) => setGeminiChecks((current) => ({ ...current, keyIntegrity: event.target.checked }))} /> Confirmei que a chave não foi comprometida pelo ZIP anterior</label>
          <button
            type="button"
            disabled={!status?.enabled || geminiRunning || !Object.values(geminiChecks).every(Boolean)}
            onClick={() => void executeGeminiSmoke()}
          >
            {geminiRunning ? "Executando…" : "Executar uma chamada sintética"}
          </button>
          {geminiResult && (
            <div className={`obs-gemini-result ${statusTone(geminiResult.status)}`} role="status">
              <strong>{geminiResult.status} · chamadas: {geminiResult.call_count}</strong>
              <p>{geminiResult.reason ?? geminiResult.public_response ?? "Concluído sem conteúdo público."}</p>
            </div>
          )}
        </div>
      </section>

      <section className="obs-filters" aria-label="Filtros de execuções">
        <label>Origem<input value={filters.origin} onChange={(event) => updateFilter("origin", event.target.value)} placeholder="finguard" /></label>
        <label>Task<input value={filters.task} onChange={(event) => updateFilter("task", event.target.value)} placeholder="qa_report_analysis" /></label>
        <label>Status<select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}><option value="">Todos</option><option value="ok">ok</option><option value="blocked">blocked</option><option value="error">error</option><option value="disabled">disabled</option></select></label>
        <label>Provider<input value={filters.provider} onChange={(event) => updateFilter("provider", event.target.value)} placeholder="local_qa" /></label>
        <label>Fallback<select value={filters.fallback} onChange={(event) => updateFilter("fallback", event.target.value)}><option value="">Todos</option><option value="true">Sim</option><option value="false">Não</option></select></label>
        <button type="button" onClick={() => setFilters(EMPTY_FILTERS)}>Limpar</button>
        <button type="button" onClick={() => void loadExecutions()} disabled={!status?.enabled}>Atualizar</button>
      </section>

      {error && <div className="obs-error" role="alert">{error}</div>}

      <section className="obs-workspace">
        <aside className="obs-list-panel">
          <div className="obs-section-title">
            <div><span>LISTA DE EXECUÇÕES</span><strong>{loading ? "Carregando…" : `${items.length} registros`}</strong></div>
          </div>
          <div className="obs-table-wrap">
            <table>
              <thead><tr><th>Horário</th><th>Origem / task</th><th>Status</th><th>Provider</th><th>Fallback</th><th>Duração</th><th>Audit ID</th></tr></thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.execution_id} className={selectedId === item.execution_id ? "selected" : ""} onClick={() => setSelectedId(item.execution_id)}>
                    <td>{formatTimestamp(item.timestamp)}</td>
                    <td><strong>{item.origin_system}</strong><small>{item.task}</small></td>
                    <td><span className={`obs-status ${statusTone(item.status)}`}>{item.status}</span></td>
                    <td>{item.provider_effective ?? "—"}</td>
                    <td>{item.fallback ? "sim" : "não"}</td>
                    <td>{item.duration_ms.toFixed(1)} ms</td>
                    <td><code>{item.audit_id.slice(0, 8)}</code></td>
                  </tr>
                ))}
                {!loading && items.length === 0 && <tr><td colSpan={7} className="obs-empty">Nenhuma execução corresponde aos filtros.</td></tr>}
              </tbody>
            </table>
          </div>
        </aside>

        <article className="obs-detail-panel">
          {!detail ? (
            <div className="obs-empty-detail"><strong>Selecione uma execução</strong><p>Provider, fallback, memória, avaliação, release gate e timeline aparecerão aqui.</p></div>
          ) : (
            <>
              <header className="obs-detail-header">
                <div><span>DETALHE DA EXECUÇÃO</span><h1>{detail.task}</h1><p>{detail.origin_system} · {formatTimestamp(detail.timestamp)}</p></div>
                <span className={`obs-status ${statusTone(detail.status)}`}>{detail.status}</span>
              </header>

              <section className="obs-route-grid">
                <article><span>Solicitado</span><strong>{detail.provider_requested ?? "—"}</strong></article>
                <article><span>Selecionado</span><strong>{detail.provider_selected ?? "—"}</strong></article>
                <article><span>Efetivo</span><strong>{detail.provider_effective ?? "—"}</strong></article>
                <article><span>Fallback</span><strong>{detail.fallback ? "sim" : "não"}</strong></article>
                <article><span>Audit ID</span><strong title={detail.audit_id}>{detail.audit_id.slice(0, 12)}</strong></article>
                <article><span>Duração</span><strong>{detail.duration_ms.toFixed(1)} ms</strong></article>
              </section>

              <section className="obs-timeline-card">
                <h3>Timeline</h3>
                <ol>{detail.timeline.map((event, index) => <li key={`${event.stage}-${index}`}><span /><div><strong>{event.stage}</strong><small>{event.status}{event.offset_ms != null ? ` · ${event.offset_ms.toFixed(1)} ms` : ""}</small>{event.detail && <p>{event.detail}</p>}</div></li>)}</ol>
              </section>

              <section className="obs-memory-card">
                <div><span>Memória consultada</span><strong>{detail.memory_consulted ? "sim" : "não"}</strong></div>
                <div><span>Memória criada</span><strong>{detail.memory_created ? "sim" : "não"}</strong></div>
                <div><span>Memory ID</span><strong>{detail.memory_id ? detail.memory_id.slice(0, 12) : "—"}</strong></div>
              </section>

              <section className="obs-detail-grid">
                <JsonPanel title="Payload sanitizado" value={detail.payload_sanitized} />
                <JsonPanel title="Campos removidos" value={detail.removed_fields} />
                <JsonPanel title="Tentativas e fallback" value={{ attempts: detail.provider_attempts, reason: detail.fallback_reason, retry: detail.retry }} />
                <JsonPanel title="Resposta pública" value={detail.public_response} />
                <JsonPanel title="Release gate" value={detail.release_gate} />
                <JsonPanel title="Avaliação" value={detail.evaluation} />
                <JsonPanel title="Sinais extraídos" value={detail.signals} />
                <JsonPanel title="Erro sanitizado" value={detail.error} />
                <JsonPanel title="Resultado devolvido" value={detail.result_returned} />
              </section>
            </>
          )}
        </article>
      </section>
    </main>
  );
}
