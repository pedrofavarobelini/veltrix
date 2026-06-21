import { useEffect, useRef, useState } from "react";
import { getProviders, ProviderInfo, sendChatMessage } from "../services/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: {
    provider: string;
    model: string;
    fallbackUsed: boolean;
    error?: string | null;
  };
};

type FeedbackType = "like" | "dislike";

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
  config: "Config",
  assistant: "Assistente",
  helper: "Como posso ajudar hoje?",
  you: "Você",
  copy: "Copiar",
  copied: "Copiado",
  redo: "Refazer",
  liked: "Gostei",
  disliked: "Não gostei",
  inputPlaceholder: "Digite sua mensagem...",
  sending: "Enviando...",
  send: "Enviar",
  settingsTitle: "Configurações",
  settingsDescription:
    "Ajuste o provider, o modo e o prompt base usado nos testes do assistente.",
  provider: "Provider",
  model: "Modelo",
  providerHelp:
    "Providers reais exigem chave no .env. Se a chave não existir, o sistema usa fallback para Mock.",
  promptBase: "Prompt base",
  promptHelp:
    "Esse texto orienta o comportamento do PedroCore IA durante os testes.",
  cancel: "Cancelar",
  saveAndClose: "Salvar e fechar",
  typeBeforeSend: "Digite uma mensagem antes de enviar.",
  generatingAgain: "Gerando nova resposta...",
  apiError:
    "Erro ao conectar com a API. Verifique se o backend está rodando na porta 3333.",
  copySuccess: "Resposta copiada.",
  copyError: "Não foi possível copiar a resposta.",
  feedbackLike: "Feedback registrado: gostei.",
  feedbackDislike: "Feedback registrado: não gostei.",
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

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: UI.welcome,
    },
  ]);

  const [message, setMessage] = useState("");
  const [mode, setMode] = useState("tecnico");
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("mock-v1");
  const [providers, setProviders] = useState<ProviderInfo[]>(DEFAULT_PROVIDERS);
  const [systemPrompt, setSystemPrompt] = useState(UI.defaultPrompt);

  const [loading, setLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [lastMessage, setLastMessage] = useState("");
  const [toast, setToast] = useState("");
  const [feedback, setFeedback] = useState<FeedbackType | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const toastTimeoutRef = useRef<number | null>(null);
  const copiedTimeoutRef = useRef<number | null>(null);

  const selectedProvider = providers.find((item) => item.name === provider);

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
        showToast("Não foi possível carregar providers. Usando lista local.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    const text = customMessage ?? message;

    if (!text.trim()) {
      showToast(UI.typeBeforeSend);
      return;
    }

    setLastMessage(text);
    setFeedback(null);

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: text,
      },
    ]);

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

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          meta: {
            provider: response.provider,
            model: response.model,
            fallbackUsed: response.fallback_used,
            error: response.error,
          },
        },
      ]);

      if (response.fallback_used) {
        showToast("Fallback para MockProvider acionado.");
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: UI.apiError,
        },
      ]);

      showToast("Erro ao conectar com a API.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(content: string, index: number) {
    try {
      await navigator.clipboard.writeText(content);

      if (copiedTimeoutRef.current) {
        window.clearTimeout(copiedTimeoutRef.current);
      }

      setCopiedIndex(index);
      showToast(UI.copySuccess);

      copiedTimeoutRef.current = window.setTimeout(() => {
        setCopiedIndex(null);
        copiedTimeoutRef.current = null;
      }, 1800);
    } catch {
      showToast(UI.copyError);
    }
  }

  function handleFeedback(type: FeedbackType) {
    setFeedback(type);
    showToast(type === "like" ? UI.feedbackLike : UI.feedbackDislike);
  }

  return (
    <main className="app">
      {toast && <div className="toast">{toast}</div>}

      <header className="header">
        <div className="brand">
          <div className="logo">IA</div>
          <div>
            <h1>{UI.assistantName}</h1>
            <span>{UI.subtitle}</span>
          </div>
        </div>

        <div className="controls">
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

          <button onClick={() => setSettingsOpen(true)}>{UI.config}</button>
        </div>
      </header>

      <section className="hero">
        <h2>{UI.assistant}</h2>
        <p>{UI.helper}</p>
        <div className="provider-status">
          <span>Provider: {selectedProvider?.label ?? provider}</span>
          <span>Modelo: {model}</span>
          {selectedProvider && !selectedProvider.configured && selectedProvider.real_provider && (
            <span className="warning-pill">sem chave — fallback ativo</span>
          )}
        </div>
      </section>

      <section className="chat">
        {messages.map((item, index) => (
          <article
            key={`${item.role}-${index}`}
            className={`message ${item.role === "user" ? "user" : "assistant"}`}
          >
            <div className="avatar">{item.role === "user" ? "P" : "IA"}</div>

            <div className="message-content">
              <strong>{item.role === "user" ? UI.you : UI.assistantName}</strong>
              <p>{item.content}</p>

              {item.meta && (
                <div className="response-meta">
                  <span>{item.meta.provider}</span>
                  <span>{item.meta.model}</span>
                  {item.meta.fallbackUsed && <span className="warning-pill">fallback usado</span>}
                </div>
              )}

              {item.role === "assistant" && (
                <div className="actions">
                  <button onClick={() => handleCopy(item.content, index)}>
                    {copiedIndex === index ? UI.copied : UI.copy}
                  </button>

                  <button disabled={!lastMessage || loading} onClick={() => handleSend(lastMessage)}>
                    {UI.redo}
                  </button>

                  <button
                    className={feedback === "like" ? "active-feedback" : ""}
                    onClick={() => handleFeedback("like")}
                  >
                    {UI.liked}
                  </button>

                  <button
                    className={feedback === "dislike" ? "active-feedback" : ""}
                    onClick={() => handleFeedback("dislike")}
                  >
                    {UI.disliked}
                  </button>
                </div>
              )}
            </div>
          </article>
        ))}

        {loading && (
          <article className="message assistant">
            <div className="avatar">IA</div>
            <div className="message-content">
              <strong>{UI.assistantName}</strong>
              <p>Gerando resposta...</p>
            </div>
          </article>
        )}
      </section>

      <footer className="input-area">
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder={UI.inputPlaceholder}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              handleSend();
            }
          }}
        />

        <button onClick={() => handleSend()} disabled={loading}>
          {loading ? UI.sending : UI.send}
        </button>
      </footer>

      {settingsOpen && (
        <aside className="settings">
          <div className="settings-card">
            <div className="settings-header settings-header-v102">
              <div>
                <h3>{UI.settingsTitle}</h3>
                <p>{UI.settingsDescription}</p>
              </div>

              <button className="close-button" onClick={() => setSettingsOpen(false)}>
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
              <button className="secondary-button" onClick={() => setSettingsOpen(false)}>
                {UI.cancel}
              </button>

              <button className="primary-button" onClick={() => setSettingsOpen(false)}>
                {UI.saveAndClose}
              </button>
            </div>
          </div>
        </aside>
      )}
    </main>
  );
}
