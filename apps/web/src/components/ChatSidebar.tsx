import type { ChatMessage } from "../types/chat";

type ChatSidebarProps = {
  messages: ChatMessage[];
  storedMessagesCount: number;
  providerLabel: string;
  model: string;
  fallbackWarning: boolean;
  loading: boolean;
  onClearHistory: () => void;
  onOpenSettings: () => void;
};

function formatTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function createSnippet(content: string) {
  const text = content.replace(/\s+/g, " ").trim();

  if (text.length <= 52) {
    return text;
  }

  return `${text.slice(0, 52)}...`;
}

export function ChatSidebar({
  messages,
  storedMessagesCount,
  providerLabel,
  model,
  fallbackWarning,
  loading,
  onClearHistory,
  onOpenSettings,
}: ChatSidebarProps) {
  const historyItems = messages
    .filter((item) => !item.isSystem && item.role === "user")
    .slice(-8)
    .reverse();

  return (
    <aside className="chat-sidebar" aria-label="Histórico local do PedroCore IA">
      <div className="sidebar-brand">
        <div className="sidebar-logo">P</div>
        <div>
          <strong>PedroCore IA</strong>
          <span>Interface V4</span>
        </div>
      </div>

      <button className="new-chat-button" type="button" onClick={onClearHistory} disabled={loading}>
        + Nova conversa
      </button>

      <div className="sidebar-card provider-card">
        <span className="sidebar-label">Provider ativo</span>
        <strong>{providerLabel}</strong>
        <small>{model}</small>
        {fallbackWarning && <em>Sem chave configurada — fallback possível</em>}
      </div>

      <section className="history-panel">
        <div className="history-panel-header">
          <div>
            <span className="sidebar-label">Histórico</span>
            <strong>{storedMessagesCount} mensagem(ns)</strong>
          </div>
          <button type="button" onClick={onOpenSettings}>
            Config
          </button>
        </div>

        {historyItems.length > 0 ? (
          <div className="history-list">
            {historyItems.map((item) => (
              <div className="history-item" key={item.id}>
                <span>{createSnippet(item.content)}</span>
                <small>{formatTime(item.createdAt)}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-history">Nenhuma pergunta salva ainda.</p>
        )}
      </section>

      <div className="sidebar-card storage-card">
        <span className="sidebar-label">Persistência local</span>
        <p>Histórico e feedbacks ficam salvos apenas neste navegador.</p>
        <button type="button" onClick={onClearHistory} disabled={storedMessagesCount === 0 || loading}>
          Limpar histórico
        </button>
      </div>
    </aside>
  );
}
