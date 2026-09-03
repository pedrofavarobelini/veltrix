export type ChatRole = "user" | "assistant";

export type FeedbackType = "like" | "dislike";

export type ChatMessageMeta = {
  provider: string;
  model: string;
  fallbackUsed: boolean;
  error?: string | null;
  /**
   * IA que o usuário escolheu, com o rótulo da interface. Sem isso a bolha só
   * consegue dizer QUE falhou, nunca QUEM falhou.
   */
  requestedProviderLabel?: string;
  /**
   * `true` quando o provider escolhido não concluiu e NADA respondeu no lugar
   * dele — o backend devolveu `provider="none"`. A bolha então é um aviso de
   * falha, nunca uma resposta de IA.
   */
  providerFailed?: boolean;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  meta?: ChatMessageMeta;
  feedback?: FeedbackType | null;
  isSystem?: boolean;
};
