import { useEffect, useMemo, useRef, useState } from "react";
import { ChatComposer } from "../components/ChatComposer";
import { ChatSidebar } from "../components/ChatSidebar";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingBubble } from "../components/LoadingBubble";
import { MessageBubble } from "../components/MessageBubble";
import { getProviders, sendChatMessage } from "../services/api";
import type { ProviderInfo } from "../services/api";
import type { ChatMessage, FeedbackType } from "../types/chat";
import {
  createChatMessageId,
  limitChatHistory,
  loadChatHistory,
  saveChatHistory,
  updateMessageFeedback,
} from "../utils/chatStorage";

const UI = {
  welcome:
    "Olá, eu sou o PedroCore IA. Escolha um provider e envie uma pergunta para testar minhas respostas.",
  defaultPrompt:
    "Você é o PedroCore IA, um assistente pessoal técnico, claro, direto e útil.",
  assistantName: "PedroCore IA",
  subtitle: "Assistente pessoal multi-provider",
  normal: "Normal",
  technical: "Técnico",
  summarized: "Resumido",
  code: "Código",
  config: "Configurações",
  clearHistory: "Limpar histórico",
  historyHelp: "Histórico e feedbacks salvos apenas neste navegador.",
  you: "Você",
  inputPlaceholder: "Digite sua mensagem...",
  settingsTitle: "Configurações",
  settingsDescription:
    "Ajuste provider, modo e prompt base sem expor chaves de API no frontend.",
  provider: "Provider",
  model: "Modelo",
  providerHelp:
    "Providers reais exigem chave no .env local. Se a chave não existir, o backend pode usar fallback para Mock.",
  promptBase: "Prompt base",
  promptHelp: "Esse texto orienta o comportamento do PedroCore IA durante os testes.",
  cancel: "Cancelar",
  saveAndClose: "Salvar e fechar",
  typeBeforeSend: "Digite uma mensagem antes de enviar.",
  generatingAgain: "Gerando nova resposta...",
  apiError:
    "Verifique se o backend FastAPI está aberto em http://127.0.0.1:3333 e tente novamente.",
  copySuccess: "Resposta copiada.",
  copyError: "Não foi possível copiar a resposta.",
  feedbackLike: "Feedback registrado: gostei.",
  feedbackDislike: "Feedback registrado: não gostei.",
  clearConfirm: "Tem certeza que deseja limpar o histórico local desta conversa?",
  historyCleared: "Histórico local limpo.",
  fallbackToast: "Fallback para MockProvider acionado.",
  providersError: "Não foi possível carregar providers. Usando lista local.",
  close: "×",
};

const DEFAULT_PROVIDERS: ProviderInfo[] = [
  { name: "mock", label: "Mock", default_model: "mock-v1", configured: true, real_provider: false },
  { name: "gemini", label: "Gemini", default_model: "gemini-3.5-flash", configured: false, real_provider: true },
  { name: "openai", label: "OpenAI", default_model: "gpt-5.2-mini", configured: false, real_provider: true },
  { name: "claude", label: "Claude", default_model: "claude-sonnet-4-5", configured: false, real_provider: true },
  { name: "deepseek", label: "DeepSeek", default_model: "deepseek-chat", configured: false, real_provider: true },
  { name: "grok", label: "Grok/xAI", default_model: "grok-4.3", configured: false, real_provider: true },
];

function createWelcomeMessage(): ChatMessage {
  return {
    id: "pedrocore-welcome-message",
    role: "assistant",
    content: UI.welcome,
    createdAt: new Date().toISOString(),
    feedback: null,
    isSystem: true,
  };
}

function createMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: createChatMessageId(),
    role,
    content,
    createdAt: new Date().toISOString(),
    feedback: null,
  };
}

function formatCurrentDate() {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).format(new Date());
}

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadChatHistory([createWelcomeMessage()]),
  );

  const [message, setMessage] = useState("");
  const [mode, setMode] = useState("tecnico");
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("mock-v1");
  const [providers, setProviders] = useState<ProviderInfo[]>(DEFAULT_PROVIDERS);
  const [systemPrompt, setSystemPrompt] = useState(UI.defaultPrompt);

  const [loading, setLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const toastTimeoutRef = useRef<number | null>(null);
  const copiedTimeoutRef = useRef<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const selectedProvider = providers.find((item) => item.name === provider);
  const lastUserMessage = useMemo(
    () => [...messages].reverse().find((item) => item.role === "user")?.content ?? "",
    [messages],
  );
  const storedMessagesCount = messages.filter((item) => !item.isSystem).length;
  const assistantResponsesCount = messages.filter(
    (item) => item.role === "assistant" && !item.isSystem,
  ).length;
  const likedResponsesCount = messages.filter((item) => item.feedback === "like").length;
  const dislikedResponsesCount = messages.filter((item) => item.feedback === "dislike").length;

  useEffect(() => {
    getProviders()
      .then((data) => {
        setProviders(data);
        const current = data.find((item) => item.name === provider);
        if (current) {
          setModel(current.default_model);
        }
      })
      .catch(() => {
        showToast(UI.providersError);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    saveChatHistory(messages);
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, errorMessage]);

  function showToast(text: string, duration = 2600) {
    if (toastTimeoutRef.current) {
      window.clearTimeout(toastTimeoutRef.current);
    }

    setToast(text);

    toastTimeoutRef.current = window.setTimeout(() => {
      setToast("");
      toastTimeoutRef.current = null;
    }, duration);
  }

  function handleProviderChange(value: string) {
    setProvider(value);
    const next = providers.find((item) => item.name === value);
    if (next) {
      setModel(next.default_model);
    }
  }

  async function handleSend(customMessage?: string) {
    const text = (customMessage ?? message).trim();

    if (!text) {
      showToast(UI.typeBeforeSend);
      return;
    }

    const userMessage = createMessage("user", text);

    setErrorMessage("");
    setMessages((prev) => limitChatHistory([...prev, userMessage]));
    setMessage("");
    setLoading(true);

    if (customMessage) {
      showToast(UI.generatingAgain);
    }

    try {
      const response = await sendChatMessage({
        message: text,
        mode,
        provider,
        model,
        system_prompt: systemPrompt,
      });

      const assistantMessage: ChatMessage = {
        ...createMessage("assistant", response.answer),
        meta: {
          provider: response.provider,
          model: response.model,
          fallbackUsed: response.fallback_used,
          error: response.error,
        },
      };

      setMessages((prev) => limitChatHistory([...prev, assistantMessage]));

      if (response.fallback_used) {
        showToast(UI.fallbackToast);
      }
    } catch {
      setErrorMessage(UI.apiError);
      showToast("Erro ao conectar com a API.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(content: string, messageId: string) {
    try {
      await navigator.clipboard.writeText(content);

      if (copiedTimeoutRef.current) {
        window.clearTimeout(copiedTimeoutRef.current);
      }

      setCopiedMessageId(messageId);
      showToast(UI.copySuccess);

      copiedTimeoutRef.current = window.setTimeout(() => {
        setCopiedMessageId(null);
        copiedTimeoutRef.current = null;
      }, 1800);
    } catch {
      showToast(UI.copyError);
    }
  }

  function handleFeedback(messageId: string, type: FeedbackType) {
    setMessages((prev) => updateMessageFeedback(prev, messageId, type));
    showToast(type === "like" ? UI.feedbackLike : UI.feedbackDislike);
  }

  function handleClearHistory() {
    if (storedMessagesCount > 0 && !window.confirm(UI.clearConfirm)) {
      return;
    }

    setMessages([createWelcomeMessage()]);
    setCopiedMessageId(null);
    setErrorMessage("");
    showToast(UI.historyCleared);
  }

  function handleRetry() {
    if (!lastUserMessage || loading) {
      return;
    }

    void handleSend(lastUserMessage);
  }

  return (
    <main className="app-shell">
      {toast && <div className="toast">{toast}</div>}

      <ChatSidebar
        messages={messages}
        storedMessagesCount={storedMessagesCount}
        providerLabel={selectedProvider?.label ?? provider}
        model={model}
        fallbackWarning={Boolean(selectedProvider && !selectedProvider.configured && selectedProvider.real_provider)}
        loading={loading}
        onClearHistory={handleClearHistory}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <section className="chat-workspace">
        <header className="chat-topbar">
          <div>
            <span>{formatCurrentDate()}</span>
            <h1>{UI.assistantName}</h1>
            <p>{UI.subtitle}</p>
          </div>

          <div className="topbar-controls">
            <select value={mode} onChange={(event) => setMode(event.target.value)}>
              <option value="normal">{UI.normal}</option>
              <option value="tecnico">{UI.technical}</option>
              <option value="resumido">{UI.summarized}</option>
              <option value="codigo">{UI.code}</option>
            </select>

            <select value={provider} onChange={(event) => handleProviderChange(event.target.value)}>
              {providers.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.label}{item.configured ? "" : " (sem chave)"}
                </option>
              ))}
            </select>

            <button type="button" onClick={() => setSettingsOpen(true)}>
              {UI.config}
            </button>
          </div>
        </header>

        <div className="metrics-grid" aria-label="Resumo do chat">
          <div>
            <span>Mensagens</span>
            <strong>{storedMessagesCount}</strong>
          </div>
          <div>
            <span>Respostas</span>
            <strong>{assistantResponsesCount}</strong>
          </div>
          <div>
            <span>Gostei</span>
            <strong>{likedResponsesCount}</strong>
          </div>
          <div>
            <span>Não gostei</span>
            <strong>{dislikedResponsesCount}</strong>
          </div>
        </div>

        <p className="history-help">{UI.historyHelp}</p>

        <section className="chat-panel" aria-label="Conversa atual">
          <div className="messages-list">
            {messages.map((item) => (
              <MessageBubble
                key={item.id}
                message={item}
                assistantName={UI.assistantName}
                userName={UI.you}
                copied={copiedMessageId === item.id}
                retryDisabled={!lastUserMessage || loading}
                onCopy={handleCopy}
                onFeedback={handleFeedback}
                onRetry={handleRetry}
              />
            ))}

            {loading && <LoadingBubble />}

            {errorMessage && (
              <ErrorBanner
                message={errorMessage}
                retryDisabled={!lastUserMessage || loading}
                onRetry={handleRetry}
                onDismiss={() => setErrorMessage("")}
              />
            )}

            <div ref={messagesEndRef} />
          </div>
        </section>

        <ChatComposer
          value={message}
          loading={loading}
          placeholder={UI.inputPlaceholder}
          onChange={setMessage}
          onSend={() => void handleSend()}
        />
      </section>

      {settingsOpen && (
        <aside className="settings">
          <div className="settings-card">
            <div className="settings-header">
              <div>
                <h3>{UI.settingsTitle}</h3>
                <p>{UI.settingsDescription}</p>
              </div>

              <button className="close-button" type="button" onClick={() => setSettingsOpen(false)}>
                {UI.close}
              </button>
            </div>

            <div className="settings-section">
              <label>
                {UI.provider}
                <select value={provider} onChange={(event) => handleProviderChange(event.target.value)}>
                  {providers.map((item) => (
                    <option key={item.name} value={item.name}>
                      {item.label}{item.configured ? "" : " (sem chave)"}
                    </option>
                  ))}
                </select>
              </label>
              <span className="field-help">{UI.providerHelp}</span>
            </div>

            <div className="settings-section">
              <label>
                {UI.model}
                <input value={model} onChange={(event) => setModel(event.target.value)} />
              </label>
            </div>

            <div className="settings-section">
              <label>
                {UI.promptBase}
                <textarea value={systemPrompt} onChange={(event) => setSystemPrompt(event.target.value)} />
              </label>
              <span className="field-help">{UI.promptHelp}</span>
            </div>

            <div className="settings-actions">
              <button className="secondary-button" type="button" onClick={() => setSettingsOpen(false)}>
                {UI.cancel}
              </button>

              <button className="primary-button" type="button" onClick={() => setSettingsOpen(false)}>
                {UI.saveAndClose}
              </button>
            </div>
          </div>
        </aside>
      )}
    </main>
  );
}
