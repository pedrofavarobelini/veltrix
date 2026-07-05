import { useEffect, useMemo, useRef, useState } from "react";
import pedrocoreLogo from "../assets/pedrocore-logo-icon.png";
import mockProviderLogo from "../assets/providers/mock.svg";
import geminiProviderLogo from "../assets/providers/gemini.svg";
import openaiProviderLogo from "../assets/providers/openai.svg";
import claudeProviderLogo from "../assets/providers/claude.svg";
import deepseekProviderLogo from "../assets/providers/deepseek.svg";
import grokProviderLogo from "../assets/providers/grok.svg";
import { ChatComposer } from "../components/ChatComposer";
import { ChatSidebar } from "../components/ChatSidebar";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingBubble } from "../components/LoadingBubble";
import { MessageBubble } from "../components/MessageBubble";
import { ProviderSettingsPanel } from "../components/ProviderSettingsPanel";
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
import { loadProviderSettings, saveProviderSettings } from "../utils/providerSettings";

const UI = {
  welcome:
    "Olá, eu sou o PedroCore IA. Configure seu provider, escolha um modo de resposta e envie uma pergunta para testar a nova interface.",
  defaultPrompt:
    "Você é o PedroCore IA, um assistente pessoal técnico, claro, direto e útil.",
  assistantName: "PedroCore IA",
  subtitle: "Assistente inteligente multi-provider",
  versionLabel: "V5.1.9",
  normal: "Padrão",
  technical: "Técnico",
  summarized: "Resumido",
  code: "Código",
  config: "Providers",
  clearHistory: "Limpar histórico",
  historyHelp: "Histórico, feedbacks e configurações ficam salvos apenas neste navegador.",
  you: "Você",
  inputPlaceholder: "Digite sua mensagem...",
  settingsSaved: "Configurações de provider salvas localmente.",
  modelReset: "Modelo padrão aplicado.",
  promptReset: "Prompt base restaurado.",
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
};

const PROVIDER_LOGOS: Record<string, string> = {
  mock: mockProviderLogo,
  gemini: geminiProviderLogo,
  openai: openaiProviderLogo,
  claude: claudeProviderLogo,
  deepseek: deepseekProviderLogo,
  grok: grokProviderLogo,
};

const DEFAULT_PROVIDERS: ProviderInfo[] = [
  { name: "mock", label: "Mock", default_model: "mock-v1", configured: true, real_provider: false },
  { name: "gemini", label: "Gemini", default_model: "gemini-3.5-flash", configured: false, real_provider: true },
  { name: "openai", label: "OpenAI", default_model: "gpt-5.2-mini", configured: false, real_provider: true },
  { name: "claude", label: "Claude", default_model: "claude-sonnet-4-5", configured: false, real_provider: true },
  { name: "deepseek", label: "DeepSeek", default_model: "deepseek-chat", configured: false, real_provider: true },
  { name: "grok", label: "Grok/xAI", default_model: "grok-4.3", configured: false, real_provider: true },
];

const DEFAULT_PROVIDER_SETTINGS = {
  provider: "mock",
  model: "mock-v1",
  mode: "tecnico",
  systemPrompt: UI.defaultPrompt,
};

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

  const initialProviderSettings = useMemo(
    () => loadProviderSettings(DEFAULT_PROVIDER_SETTINGS),
    [],
  );

  const [message, setMessage] = useState("");
  const [mode, setMode] = useState(initialProviderSettings.mode);
  const [provider, setProvider] = useState(initialProviderSettings.provider);
  const [model, setModel] = useState(initialProviderSettings.model);
  const [providers, setProviders] = useState<ProviderInfo[]>(DEFAULT_PROVIDERS);
  const [systemPrompt, setSystemPrompt] = useState(initialProviderSettings.systemPrompt);
  const [allowRealProvider, setAllowRealProvider] = useState(false);

  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const toastTimeoutRef = useRef<number | null>(null);
  const copiedTimeoutRef = useRef<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const providerDockRef = useRef<HTMLElement | null>(null);

  const selectedProvider = providers.find((item) => item.name === provider);
  const selectedProviderIsReal = Boolean(selectedProvider?.real_provider);
  const lastUserMessage = useMemo(
    () => [...messages].reverse().find((item) => item.role === "user")?.content ?? "",
    [messages],
  );
  const storedMessagesCount = messages.filter((item) => !item.isSystem).length;

  useEffect(() => {
    getProviders()
      .then((data) => {
        setProviders(data);
        const current = data.find((item) => item.name === provider);
        if (current) {
          setModel((currentModel) => currentModel.trim() || current.default_model);
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
    saveProviderSettings({ provider, model, mode, systemPrompt });
  }, [provider, model, mode, systemPrompt]);

  useEffect(() => {
    if (!selectedProviderIsReal) {
      setAllowRealProvider(false);
    }
  }, [selectedProviderIsReal]);

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
    setAllowRealProvider(false);
    const next = providers.find((item) => item.name === value);
    if (next) {
      setModel(next.default_model);
    }
  }

  function handleResetModel() {
    const current = providers.find((item) => item.name === provider);
    if (!current) {
      return;
    }

    setModel(current.default_model);
    showToast(UI.modelReset);
  }

  function handleResetPrompt() {
    setSystemPrompt(UI.defaultPrompt);
    showToast(UI.promptReset);
  }

  function handleSaveSettings() {
    saveProviderSettings({ provider, model, mode, systemPrompt });
    showToast(UI.settingsSaved);
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
        allow_real_provider: selectedProviderIsReal && allowRealProvider,
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
      setAllowRealProvider(false);
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
    <main className="app-shell v51-redesign">
      {toast && <div className="toast">{toast}</div>}

      <header className="reference-brandbar" aria-label="Marca PedroCore IA">
        <div className="reference-brand">
          <img src={pedrocoreLogo} alt="Logo oficial do PedroCore IA" />
          <div>
            <strong>PedroCore <span>IA</span></strong>
          </div>
        </div>
      </header>

      <section className="console-window">
        <div className="console-window-bar">
          <div className="window-title" aria-hidden="true" />
        </div>

        <div className="console-frame">
          <ChatSidebar
            messages={messages}
            storedMessagesCount={storedMessagesCount}
            providerLabel={selectedProvider?.label ?? provider}
            model={model}
            versionLabel={UI.versionLabel}
            providerConfigured={Boolean(selectedProvider?.configured)}
            realProvider={Boolean(selectedProvider?.real_provider)}
            fallbackWarning={Boolean(selectedProvider && !selectedProvider.configured && selectedProvider.real_provider)}
            loading={loading}
            onClearHistory={handleClearHistory}
          />

          <section className="chat-workspace">
            <header className="chat-topbar">
              <div>
                <span>{formatCurrentDate()}</span>
                <h1>Chat com PedroCore <span>IA</span></h1>
                <p>{UI.subtitle}</p>
              </div>
            </header>

            <div className="provider-strip" aria-label="Providers disponíveis">
              {providers.slice(0, 6).map((item) => {
                const active = item.name === provider;
                const status = !item.real_provider ? "Mock local" : item.configured ? "Config." : "Sem chave";

                return (
                  <button
                    key={item.name}
                    type="button"
                    className={`provider-tile ${active ? "active" : ""} ${!item.configured && item.real_provider ? "provider-warning" : ""}`}
                    onClick={() => handleProviderChange(item.name)}
                    disabled={loading}
                  >
                    <span>
                      {PROVIDER_LOGOS[item.name] ? (
                        <img src={PROVIDER_LOGOS[item.name]} alt={`${item.label} logo`} />
                      ) : (
                        item.label.slice(0, 2)
                      )}
                    </span>
                    <strong>{item.label}</strong>
                    <small>{status}</small>
                  </button>
                );
              })}
            </div>

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

          <ProviderSettingsPanel
            panelRef={providerDockRef}
            providers={providers}
            provider={provider}
            model={model}
            mode={mode}
            systemPrompt={systemPrompt}
            defaultSystemPrompt={UI.defaultPrompt}
            loading={loading}
            allowRealProvider={allowRealProvider}
            onProviderChange={handleProviderChange}
            onModelChange={setModel}
            onModeChange={setMode}
            onSystemPromptChange={setSystemPrompt}
            onAllowRealProviderChange={setAllowRealProvider}
            onResetModel={handleResetModel}
            onResetPrompt={handleResetPrompt}
            onClose={handleSaveSettings}
            onSave={handleSaveSettings}
          />
        </div>
      </section>
    </main>
  );
}
