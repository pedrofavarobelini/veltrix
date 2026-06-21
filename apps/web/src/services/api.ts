export type ChatRequest = {
  message: string;
  mode: string;
  provider: string;
  model?: string;
  system_prompt?: string;
};

export type ChatResponse = {
  answer: string;
  provider: string;
  model: string;
  mode: string;
  requested_provider: string;
  fallback_used: boolean;
  error?: string | null;
};

export type ProviderInfo = {
  name: string;
  label: string;
  default_model: string;
  configured: boolean;
  real_provider: boolean;
};

const API_URL = "http://localhost:3333/api";

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
