import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import veltrixLogo from "../assets/veltrix-logo-icon.png";
import { ChatComposer } from "../components/ChatComposer";
import { ChatSidebar } from "../components/ChatSidebar";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingBubble } from "../components/LoadingBubble";
import { MessageBubble } from "../components/MessageBubble";
import { ProviderSettingsPanel } from "../components/ProviderSettingsPanel";
import { SettingsDrawer } from "../components/SettingsDrawer";
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
import type { ProviderSettings } from "../utils/providerSettings";
import {
  filterInternalProviders,
  filterOfferedProviders,
  filterPublicAiProviders,
  isDevProviderId,
  isPublicAiProviderId,
  isSelectableProviderId,
} from "../utils/publicProviders";
import { readTextAttachments, toArtifactInputs } from "../utils/attachments";
import type { TextAttachment } from "../utils/attachments";

const UI = {
  welcome:
    "Olá, eu sou o Veltrix. Configure seu provider, escolha um modo de resposta e envie uma pergunta para testar a nova interface.",
  defaultPrompt:
    "Você é o Veltrix, um assistente pessoal técnico, claro, direto e útil.",
  assistantName: "Veltrix",
  subtitle: "Assistente inteligente multi-provider",
  // Linha de produto 5.x; minor porque esta frente acrescenta recursos de UX
  // (composer, drawer, voz, anexos) sem quebrar contrato de API.
  versionLabel: "V5.2.0",
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
  settingsButton: "Configurações",
  settingsTitle: "Configurações",
  selectProviderNotice:
    "Nenhuma IA selecionada. Escolha uma IA no seletor abaixo para enviar mensagens.",
  authorizationNotice:
    "O uso real desta IA precisa ser ativado em Configurações antes de enviar.",
  devProviderNotice:
    "Ambiente técnico de desenvolvimento: as respostas vêm do provider interno do pipeline, não de uma IA real.",
  attachmentsRejected: "Alguns arquivos não foram anexados.",
  attachmentsAdded: "Anexo pronto para envio.",
};

const DEFAULT_PROVIDERS: ProviderInfo[] = [
  { name: "mock", label: "Mock", default_model: "mock-v1", configured: true, real_provider: false },
  { name: "gemini", label: "Gemini", default_model: "gemini-3.5-flash", configured: false, real_provider: true },
  { name: "openai", label: "OpenAI", default_model: "gpt-5.2-mini", configured: false, real_provider: true },
  { name: "claude", label: "Claude", default_model: "claude-sonnet-4-5", configured: false, real_provider: true },
  { name: "deepseek", label: "DeepSeek", default_model: "deepseek-chat", configured: false, real_provider: true },
  { name: "grok", label: "Grok/xAI", default_model: "grok-4.3", configured: false, real_provider: true },
];

const DEFAULT_PROVIDER_SETTINGS: ProviderSettings = {
  // Continua `mock` de propósito: o padrão seguro não é um provider real. A UI
  // mostra "Selecionar IA" enquanto o provider ativo não for público, em vez de
  // fingir que o Gemini está selecionado.
  provider: "mock",
  model: "mock-v1",
  mode: "tecnico",
  systemPrompt: UI.defaultPrompt,
  authorizedRealProvider: null,
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
  // Persistimos QUAL provider foi autorizado, não um booleano global. Assim a
  // autorização sobrevive ao F5 sem nunca vazar de um provider para outro.
  const [authorizedRealProvider, setAuthorizedRealProvider] = useState<string | null>(
    initialProviderSettings.authorizedRealProvider,
  );
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Anexos vivem apenas nesta mensagem: não são persistidos no histórico local
  // nem restaurados no F5. O conteúdo de um arquivo do usuário não deve ficar
  // guardado no navegador depois que a mensagem foi enviada.
  const [attachments, setAttachments] = useState<TextAttachment[]>([]);

  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const toastTimeoutRef = useRef<number | null>(null);
  const copiedTimeoutRef = useRef<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);
  // Espelho dos anexos atuais. Mantém `handleAttachmentsSelected` estável para
  // o composer e, ainda assim, enxergando a lista mais recente ao aplicar as
  // cotas de quantidade e de tamanho total.
  const attachmentsRef = useRef<TextAttachment[]>(attachments);

  attachmentsRef.current = attachments;

  const selectedProvider = providers.find((item) => item.name === provider);
  const selectedProviderIsReal = Boolean(selectedProvider?.real_provider);
  // Catálogo interno permanece intacto em `providers`; `publicProviders` é a
  // única lista que a interface oferece como IA escolhível.
  // IAs externas conhecidas — configuradas ou não. É o catálogo das Configurações.
  const publicAiProviders = useMemo(() => filterPublicAiProviders(providers), [providers]);
  // Infraestrutura interna: mock, local_qa, local_model, auto.
  const internalProviders = useMemo(() => filterInternalProviders(providers), [providers]);
  // O que o composer OFERECE no seletor. Na build pública são as IAs públicas
  // (as indisponíveis aparecem desabilitadas); em desenvolvimento soma os
  // internos que de fato respondem uma conversa.
  const offeredProviders = useMemo(() => filterOfferedProviders(providers), [providers]);
  const providerIsPublicAi = isPublicAiProviderId(provider);
  // SELECIONÁVEL é diferente de visível: exige homologação e `configured=true`
  // vindo do backend. Uma IA catalogada sem chave é visível e não selecionável.
  const providerIsSelectable = isSelectableProviderId(provider, providers);
  // Provider interno liberado só em desenvolvimento. `isSelectableProviderId`
  // já embutiu a checagem de ambiente, então um provider interno só chega aqui
  // como `true` quando a build é de desenvolvimento.
  const providerIsDev = providerIsSelectable && isDevProviderId(provider);

  // Valor DERIVADO, não estado. A autorização só vale se o ID persistido
  // corresponder ao provider atual, esse provider ainda for real e ainda for
  // válido para a UI pública. Qualquer uma das três condições caindo, o
  // consentimento deixa de valer sem precisar de sincronização manual.
  const allowRealProvider =
    authorizedRealProvider !== null &&
    authorizedRealProvider === provider &&
    selectedProviderIsReal &&
    providerIsPublicAi;

  // Um provider real sem autorização vigente resultaria em fallback Mock no
  // backend enquanto a UI mostra Gemini. Bloqueamos antes de enviar.
  //
  // Provider interno de desenvolvimento não passa por aqui de propósito: ele
  // não é real (`real_provider=false`), não usa chave e não faz chamada
  // externa, então não há uso real a consentir. Era exatamente esta a
  // incoerência anterior — o drawer oferecia o provider e o composer travava o
  // envio sem que houvesse autorização possível de conceder.
  const needsAuthorization = providerIsSelectable && selectedProviderIsReal && !allowRealProvider;
  const canSend = !loading && providerIsSelectable && !needsAuthorization;
  // Uma IA pública selecionada porém indisponível merece o motivo REAL, não o
  // genérico "nenhuma IA selecionada" — o usuário escolheu algo, e precisa
  // saber que falta configurar a chave no backend.
  const unavailablePublicAi =
    providerIsPublicAi && !providerIsSelectable ? selectedProvider : undefined;
  const composerNotice = unavailablePublicAi
    ? `${unavailablePublicAi.label} não está disponível: ${
        unavailablePublicAi.configured
          ? "provider ainda não homologado para uso real."
          : "configure a credencial no .env do backend."
      }`
    : !providerIsSelectable
      ? UI.selectProviderNotice
      : needsAuthorization
        ? UI.authorizationNotice
        : providerIsDev
          ? UI.devProviderNotice
          : "";
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
    saveProviderSettings({ provider, model, mode, systemPrompt, authorizedRealProvider });
  }, [provider, model, mode, systemPrompt, authorizedRealProvider]);

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
    // Trocar de provider nunca herda a autorização do anterior.
    setAuthorizedRealProvider(null);
    const next = providers.find((item) => item.name === value);
    if (next) {
      setModel(next.default_model);
    }
  }

  function handleAllowRealProviderChange(allowed: boolean) {
    setAuthorizedRealProvider(allowed ? provider : null);
  }

  const handleCloseSettings = useCallback(() => setSettingsOpen(false), []);

  // A validação e a leitura ficam em `utils/attachments`; aqui só entram o
  // estado e o retorno visível. O resultado carrega recusados junto com
  // aceitos para que um arquivo grande demais não derrube os outros da mesma
  // seleção — e para que o usuário saiba qual caiu e por quê.
  const handleAttachmentsSelected = useCallback(async (files: File[]) => {
    const result = await readTextAttachments(files, attachmentsRef.current);

    if (result.accepted.length > 0) {
      setAttachments((prev) => [...prev, ...result.accepted]);
    }

    if (result.rejected.length > 0) {
      const [first] = result.rejected;
      showToast(`${first.name}: ${first.reason}`, 4200);
    } else if (result.accepted.length > 0) {
      showToast(UI.attachmentsAdded);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAttachmentRemove = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((item) => item.id !== id));
  }, []);

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
    saveProviderSettings({ provider, model, mode, systemPrompt, authorizedRealProvider });
    showToast(UI.settingsSaved);
  }

  async function handleSend(customMessage?: string) {
    const text = (customMessage ?? message).trim();
    // "Refazer" repete só a pergunta: os anexos daquela mensagem já foram
    // consumidos e não estão mais no composer.
    const outgoingAttachments = customMessage ? [] : attachments;

    if (!text && outgoingAttachments.length === 0) {
      showToast(UI.typeBeforeSend);
      return;
    }

    // Guardas de verdade de estado: a UI nunca envia algo que possa voltar como
    // Mock enquanto mostra outra IA no composer.
    if (!providerIsSelectable) {
      showToast(UI.selectProviderNotice);
      return;
    }

    if (needsAuthorization) {
      showToast(UI.authorizationNotice);
      return;
    }

    // `ChatRequest.message` tem `min_length=1` no backend: uma mensagem só de
    // anexos precisa de um texto real, senão a requisição volta 422. O texto
    // sintetizado descreve o que o usuário de fato fez.
    const outgoingText =
      text ||
      `Analise o conteúdo anexado: ${outgoingAttachments.map((item) => item.name).join(", ")}.`;

    const userMessage = createMessage("user", outgoingText);

    setErrorMessage("");
    setMessages((prev) => limitChatHistory([...prev, userMessage]));
    setMessage("");
    setLoading(true);

    if (customMessage) {
      showToast(UI.generatingAgain);
    }

    try {
      const response = await sendChatMessage({
        message: outgoingText,
        mode,
        provider,
        model,
        system_prompt: systemPrompt,
        allow_real_provider: selectedProviderIsReal && allowRealProvider,
        ...(outgoingAttachments.length > 0
          ? { artifacts: toArtifactInputs(outgoingAttachments) }
          : {}),
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
      // Anexos são limpos apenas no sucesso. Falhando, eles continuam no
      // composer e o usuário pode reenviar sem escolher os arquivos de novo.
      setAttachments([]);

      if (response.fallback_used) {
        showToast(UI.fallbackToast);
      } else if (response.artifact_warnings && response.artifact_warnings.length > 0) {
        showToast(response.artifact_warnings[0], 4200);
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
    if (!lastUserMessage || !canSend) {
      return;
    }

    void handleSend(lastUserMessage);
  }

  return (
    <main className="app-shell v51-redesign">
      {toast && <div className="toast">{toast}</div>}

      <header className="reference-brandbar" aria-label="Marca Veltrix">
        <div className="reference-brand">
          <img src={veltrixLogo} alt="Logo oficial do Veltrix" />
          <div>
            <strong>Veltrix <span>IA</span></strong>
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
            versionLabel={UI.versionLabel}
            loading={loading}
            onClearHistory={handleClearHistory}
          />

          <section className="chat-workspace">
            <header className="chat-topbar">
              <div>
                <span>{formatCurrentDate()}</span>
                <h1>Chat com Veltrix <span>IA</span></h1>
                <p>{UI.subtitle}</p>
              </div>
              <button
                ref={settingsButtonRef}
                className="settings-trigger"
                type="button"
                onClick={() => setSettingsOpen(true)}
                aria-haspopup="dialog"
                aria-expanded={settingsOpen}
              >
                <span aria-hidden="true">⚙</span> {UI.settingsButton}
              </button>
            </header>

            <section className="chat-panel" aria-label="Conversa atual">
              <div className="messages-list">
                {messages.map((item) => (
                  <MessageBubble
                    key={item.id}
                    message={item}
                    assistantName={UI.assistantName}
                    userName={UI.you}
                    copied={copiedMessageId === item.id}
                    retryDisabled={!lastUserMessage || !canSend}
                    onCopy={handleCopy}
                    onFeedback={handleFeedback}
                    onRetry={handleRetry}
                  />
                ))}

                {loading && <LoadingBubble />}

                {errorMessage && (
                  <ErrorBanner
                    message={errorMessage}
                    retryDisabled={!lastUserMessage || !canSend}
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
              offeredProviders={offeredProviders}
              provider={provider}
              providerIsSelectable={providerIsSelectable}
              providerIsDev={providerIsDev}
              notice={composerNotice}
              canSend={canSend}
              attachments={attachments}
              onChange={setMessage}
              onProviderChange={handleProviderChange}
              onSend={() => void handleSend()}
              onAttachmentsSelected={(files) => void handleAttachmentsSelected(files)}
              onAttachmentRemove={handleAttachmentRemove}
            />
          </section>
        </div>
      </section>

      <SettingsDrawer open={settingsOpen} title={UI.settingsTitle} onClose={handleCloseSettings}>
        <ProviderSettingsPanel
          providers={providers}
          publicAiProviders={publicAiProviders}
          internalProviders={internalProviders}
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
          onAllowRealProviderChange={handleAllowRealProviderChange}
          onResetModel={handleResetModel}
          onResetPrompt={handleResetPrompt}
          onClose={handleCloseSettings}
          onSave={handleSaveSettings}
        />
      </SettingsDrawer>
    </main>
  );
}
