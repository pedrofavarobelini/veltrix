/**
 * Artefato textual enviado junto da mensagem.
 *
 * Espelha `ArtifactInput` do backend (`modules/artifacts/schemas.py`). Existe
 * desde a frente de artefatos e já é o transporte usado por FinGuard e
 * Structa — os anexos do composer entram por aqui, sem endpoint novo.
 *
 * `metadata` é intencionalmente omitido: o backend REJEITA o artefato inteiro
 * quando encontra chave de caminho de arquivo, e o composer não tem o que
 * enviar além de nome e conteúdo.
 */
export type ArtifactInput = {
  type: string;
  name?: string;
  content?: string;
};

export type ChatRequest = {
  message: string;
  mode: string;
  provider: string;
  model?: string;
  system_prompt?: string;
  allow_real_provider?: boolean;
  artifacts?: ArtifactInput[];
};

export type ChatResponse = {
  answer: string;
  provider: string;
  model: string;
  mode: string;
  requested_provider: string;
  fallback_used: boolean;
  safe_mode_blocked?: boolean;
  warning_codes?: string[];
  status?: string;
  error?: string | null;
  /** Avisos do processamento de artefatos (truncamento, tipo desconhecido, …). */
  artifact_warnings?: string[];
};

export type ProviderInfo = {
  name: string;
  label: string;
  default_model: string;
  configured: boolean;
  real_provider: boolean;
};

export type ExecutionSummary = {
  execution_id: string;
  audit_id: string;
  timestamp: string;
  origin_system: string;
  task: string;
  status: string;
  provider_effective?: string | null;
  fallback: boolean;
  duration_ms: number;
};

export type TimelineEvent = {
  stage: string;
  status: string;
  detail?: string | null;
  offset_ms?: number | null;
};

export type ProviderAttempt = {
  provider: string;
  result: string;
  detail?: string | null;
};

export type ExecutionDetail = ExecutionSummary & {
  payload_sanitized: Record<string, unknown>;
  removed_fields: string[];
  provider_requested?: string | null;
  provider_selected?: string | null;
  provider_attempts: ProviderAttempt[];
  fallback_reason?: string | null;
  public_response?: string | null;
  release_gate?: Record<string, unknown> | null;
  evaluation?: Record<string, unknown> | null;
  signals: Array<Record<string, unknown>>;
  memory_consulted: boolean;
  memory_created: boolean;
  memory_id?: string | null;
  error?: string | null;
  retry: Record<string, unknown>;
  timeline: TimelineEvent[];
  result_returned: Record<string, unknown>;
};

export type ObservabilityStatus = {
  enabled: boolean;
  mode: string;
  storage: string;
  max_entries: number;
  local_only: boolean;
  training_implemented: boolean;
  notice: string;
};

export type GeminiSmokeResponse = {
  status: "ok" | "blocked" | "fallback";
  executed: boolean;
  call_count: number;
  provider: string;
  model?: string | null;
  fallback: boolean;
  reason?: string | null;
  public_response?: string | null;
  notices: string[];
};

export type ExecutionFilters = {
  origin?: string;
  task?: string;
  status?: string;
  provider?: string;
  fallback?: "" | "true" | "false";
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:3333/api";

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Erro ao enviar mensagem para a IA.");
  }

  return response.json();
}

export async function getProviders(): Promise<ProviderInfo[]> {
  const response = await fetch(`${API_URL}/providers`);

  if (!response.ok) {
    throw new Error("Erro ao buscar providers.");
  }

  return response.json();
}

export async function getObservabilityStatus(): Promise<ObservabilityStatus> {
  const response = await fetch(`${API_URL}/observability/status`);
  if (!response.ok) {
    throw new Error("Não foi possível consultar o modo de observabilidade.");
  }
  return response.json();
}

export async function getExecutions(filters: ExecutionFilters): Promise<ExecutionSummary[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  params.set("limit", "200");
  const response = await fetch(`${API_URL}/observability/executions?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Observabilidade local indisponível ou desabilitada.");
  }
  const data = await response.json();
  return data.items;
}

export async function getExecutionDetail(executionId: string): Promise<ExecutionDetail> {
  const response = await fetch(`${API_URL}/observability/executions/${encodeURIComponent(executionId)}`);
  if (!response.ok) {
    throw new Error("Não foi possível carregar o detalhe da execução.");
  }
  return response.json();
}

export async function runGeminiSmoke(confirmations: {
  network: boolean;
  cost: boolean;
  keyIntegrity: boolean;
}): Promise<GeminiSmokeResponse> {
  const response = await fetch(`${API_URL}/observability/gemini-smoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      synthetic_payload: "PEDROCORE_GEMINI_SMOKE_V1",
      confirm_network: confirmations.network,
      confirm_possible_cost: confirmations.cost,
      confirm_key_not_compromised: confirmations.keyIntegrity,
    }),
  });
  if (!response.ok) {
    throw new Error("Smoke Gemini indisponível neste ambiente.");
  }
  return response.json();
}
