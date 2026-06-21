import pedrocoreLogo from "../assets/pedrocore-logo-icon.png";
import type { ChatMessage } from "../types/chat";

type ChatSidebarProps = {
  messages: ChatMessage[];
  storedMessagesCount: number;
  providerLabel: string;
  model: string;
  versionLabel: string;
  providerConfigured: boolean;
  realProvider: boolean;
  fallbackWarning: boolean;
  loading: boolean;
  onClearHistory: () => void;
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

  if (text.length <= 42) {
    return text;
  }

  return `${text.slice(0, 42)}...`;
}

export function ChatSidebar({
  messages,
  storedMessagesCount,
  providerLabel,
  model,
  versionLabel,
  providerConfigured,
  realProvider,
  fallbackWarning,
  loading,
  onClearHistory,
}: ChatSidebarProps) {
  const historyItems = messages
    .filter((item) => !item.isSystem && item.role === "user")
    .slice(-8)
    .reverse();

  const providerStatus = !realProvider ? "Mock local" : providerConfigured ? "Configurado" : "Sem chave";

  return (
    <aside className="chat-sidebar" aria-label="Navegação e histórico local do PedroCore IA">
      <div className="sidebar-brand">
        <img className="sidebar-logo brand-logo-image" src={pedrocoreLogo} alt="Logo oficial do PedroCore IA" />
        <div>
          <strong>PedroCore <span>IA</span></strong>
          <small>{versionLabel}</small>
        </div>
      </div>

      <button className="new-chat-button" type="button" onClick={onClearHistory} disabled={loading}>
        <span>+</span> Nova conversa
      </button>

      <div className="sidebar-divider" />

      <section className="history-panel">
        <div className="history-panel-header">
          <div>
            <span className="sidebar-label">Conversas recentes</span>
            <strong>{storedMessagesCount} mensagem(ns)</strong>
          </div>
        </div>

        {historyItems.length > 0 ? (
          <div className="history-list">
            {historyItems.map((item) => (
              <div className="history-item" key={item.id}>
                <span>☰ {createSnippet(item.content)}</span>
                <small>{formatTime(item.createdAt)}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-history">Nenhuma pergunta salva ainda.</p>
        )}
      </section>

      <div className="sidebar-card provider-card">
        <span className="sidebar-label">Provider ativo</span>
        <strong>{providerLabel}</strong>
        <small>{model}</small>
        <span className={`provider-mini-status ${!realProvider ? "status-mock" : providerConfigured ? "status-ok" : "status-warning"}`}>
          {providerStatus}
        </span>
        {fallbackWarning && <em>Sem chave configurada — fallback possível</em>}
      </div>

      <div className="sidebar-card storage-card">
        <span className="sidebar-label">Configurações salvas localmente</span>
        <p>Histórico, feedbacks e providers ficam somente neste navegador.</p>
        <button type="button" onClick={onClearHistory} disabled={storedMessagesCount === 0 || loading}>
          Limpar histórico
        </button>
      </div>
    </aside>
  );
}
