import veltrixLogo from "../assets/veltrix-logo-icon.png";
import type { ChatMessage, FeedbackType } from "../types/chat";

type MessageBubbleProps = {
  message: ChatMessage;
  assistantName: string;
  userName: string;
  copied: boolean;
  retryDisabled: boolean;
  onCopy: (content: string, messageId: string) => void;
  onFeedback: (messageId: string, type: FeedbackType) => void;
  onRetry: () => void;
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

export function MessageBubble({
  message,
  assistantName,
  userName,
  copied,
  retryDisabled,
  onCopy,
  onFeedback,
  onRetry,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAssistantActionable = message.role === "assistant" && !message.isSystem;
  // Falha do provider NÃO é resposta de IA: a bolha muda de natureza, e as
  // ações de opinião (Gostei/Não gostei) somem — não há resposta a avaliar.
  const providerFailed = Boolean(message.meta?.providerFailed);
  const failedProviderLabel =
    message.meta?.requestedProviderLabel ?? message.meta?.provider ?? "";

  return (
    <article className={`message-row ${isUser ? "from-user" : "from-assistant"}`}>
      {!isUser && (
        <img className="message-avatar brand-logo-image" src={veltrixLogo} alt="Veltrix" />
      )}

      <div className={`message-bubble ${providerFailed ? "provider-failed" : ""}`}>
        <div className="message-heading">
          <strong>{isUser ? userName : assistantName}</strong>
          <span>{formatTime(message.createdAt)}</span>
        </div>

        {providerFailed && (
          <p className="provider-failure-title" role="alert">
            {failedProviderLabel} não concluiu a solicitação.
          </p>
        )}

        <p>{message.content}</p>

        {message.meta && (
          <div className="response-meta">
            {/* Provider EFETIVO. `none` é o estado honesto de "ninguém
                respondeu" — nunca o nome da IA que o usuário escolheu. */}
            <span>{message.meta.provider}</span>
            <span>{message.meta.model}</span>
            {providerFailed && (
              <span className="error-pill">{failedProviderLabel} falhou</span>
            )}
            {message.meta.fallbackUsed && <span className="warning-pill">fallback local usado</span>}
            {!providerFailed && message.meta.error && (
              <span className="error-pill">erro tratado</span>
            )}
          </div>
        )}

        {isAssistantActionable && (
          <div className="message-actions">
            <button type="button" onClick={() => onCopy(message.content, message.id)}>
              {copied ? "Copiado" : "Copiar"}
            </button>

            <button type="button" disabled={retryDisabled} onClick={onRetry}>
              Refazer
            </button>

            {!providerFailed && (
              <>
                <button
                  type="button"
                  className={message.feedback === "like" ? "active-feedback" : ""}
                  onClick={() => onFeedback(message.id, "like")}
                >
                  Gostei
                </button>

                <button
                  type="button"
                  className={message.feedback === "dislike" ? "active-feedback dislike" : ""}
                  onClick={() => onFeedback(message.id, "dislike")}
                >
                  Não gostei
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
