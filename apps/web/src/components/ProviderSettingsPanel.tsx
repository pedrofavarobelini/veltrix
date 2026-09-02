import mockLogo from "../assets/providers/mock.svg";
import geminiLogo from "../assets/providers/gemini.svg";
import openaiLogo from "../assets/providers/openai.svg";
import claudeLogo from "../assets/providers/claude.svg";
import deepseekLogo from "../assets/providers/deepseek.svg";
import grokLogo from "../assets/providers/grok.svg";
import type { ProviderInfo } from "../services/api";
import {
  isDevProviderId,
  isHomologatedProviderId,
  isSelectableProvider,
} from "../utils/publicProviders";

const MODE_OPTIONS = [
  { value: "normal", label: "Padrão", description: "Resposta equilibrada para uso geral." },
  { value: "tecnico", label: "Técnica", description: "Mais precisão, contexto técnico e justificativa." },
  { value: "resumido", label: "Precisa", description: "Resposta curta, objetiva e sem rodeio." },
  { value: "codigo", label: "Código", description: "Foco em programação, exemplos e correções." },
];

const PROVIDER_ICONS: Record<string, string> = {
  mock: mockLogo,
  gemini: geminiLogo,
  openai: openaiLogo,
  claude: claudeLogo,
  deepseek: deepseekLogo,
  grok: grokLogo,
};

type ProviderSettingsPanelProps = {
  /** Catálogo completo — usado apenas para consultar status do provider ativo. */
  providers: ProviderInfo[];
  /** IAs externas públicas conhecidas, configuradas ou não. */
  publicAiProviders: ProviderInfo[];
  /** Infraestrutura interna do pipeline; exibida somente em desenvolvimento. */
  internalProviders: ProviderInfo[];
  provider: string;
  model: string;
  mode: string;
  systemPrompt: string;
  defaultSystemPrompt: string;
  loading: boolean;
  allowRealProvider: boolean;
  onProviderChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onModeChange: (value: string) => void;
  onSystemPromptChange: (value: string) => void;
  onAllowRealProviderChange: (value: boolean) => void;
  onResetModel: () => void;
  onResetPrompt: () => void;
  onClose: () => void;
  onSave: () => void;
};

/**
 * Estado factual do provider, derivado do que `/api/providers` informou.
 *
 * Distingue três situações que a versão anterior colapsava: sem chave,
 * configurado mas ainda não homologado, e pronto para uso.
 */
function getProviderStatus(provider: ProviderInfo) {
  if (!provider.real_provider) {
    return {
      label: "Mock local",
      description: "Provider seguro para testes sem chave externa.",
      className: "status-mock",
    };
  }

  if (!provider.configured) {
    return {
      label: "Não configurado",
      description: "Sem credencial no .env do backend; não pode ser usado.",
      className: "status-warning",
    };
  }

  if (!isHomologatedProviderId(provider.name)) {
    return {
      label: "Não homologado",
      description: "Credencial detectada, mas o provider ainda não foi homologado.",
      className: "status-warning",
    };
  }

  return {
    label: "Configurado",
    description: "Chave detectada no .env local do backend.",
    className: "status-ok",
  };
}

export function ProviderSettingsPanel({
  providers,
  publicAiProviders,
  internalProviders,
  provider,
  model,
  mode,
  systemPrompt,
  defaultSystemPrompt,
  loading,
  allowRealProvider,
  onProviderChange,
  onModelChange,
  onModeChange,
  onSystemPromptChange,
  onAllowRealProviderChange,
  onResetModel,
  onResetPrompt,
  onClose,
  onSave,
}: ProviderSettingsPanelProps) {
  const selectedProvider = providers.find((item) => item.name === provider);
  const selectedStatus = selectedProvider ? getProviderStatus(selectedProvider) : null;
  const selectedMode = MODE_OPTIONS.find((item) => item.value === mode) ?? MODE_OPTIONS[0];
  // Controle de apresentação, não de segurança: apenas mantém a área técnica
  // fora da experiência principal na build pública.
  const showInternalArea = import.meta.env.DEV && internalProviders.length > 0;

  return (
    <div className="settings-panel">
      <section className="dock-section">
        <span className="dock-label">Provedores de IA</span>
        <p className="provider-grid-copy">
          IAs externas conhecidas pelo Veltrix. Uma IA sem credencial no backend
          continua listada, com o estado real — some da tela seria esconder que ela
          existe. Para habilitar, configure a chave no <code>.env</code> do backend:
          a interface reage sozinha.
        </p>
        <div className="provider-card-grid">
          {publicAiProviders.map((item) => {
            const status = getProviderStatus(item);
            const active = item.name === provider;
            const usable = isSelectableProvider(item);

            return (
              <button
                className={`provider-card-option ${active ? "active-provider" : ""} ${
                  usable ? "" : "provider-unavailable"
                }`}
                type="button"
                key={item.name}
                onClick={() => onProviderChange(item.name)}
                disabled={loading || !usable}
                aria-pressed={active}
                title={usable ? undefined : status.description}
              >
                <span className="provider-icon">
                  {PROVIDER_ICONS[item.name] ? (
                    <img src={PROVIDER_ICONS[item.name]} alt="" />
                  ) : (
                    item.label.slice(0, 2)
                  )}
                </span>
                <strong>{item.label}</strong>
                <small>{item.default_model}</small>
                <em className={status.className}>{status.label}</em>
              </button>
            );
          })}
        </div>
      </section>

      <section className="dock-section">
        <label htmlFor="settings-model">Modelo</label>
        <div className="inline-field-action">
          <input
            id="settings-model"
            value={model}
            onChange={(event) => onModelChange(event.target.value)}
            disabled={loading}
          />
          <button type="button" onClick={onResetModel} disabled={loading || !selectedProvider}>
            Padrão
          </button>
        </div>
        {selectedStatus && <span className={`provider-status ${selectedStatus.className}`}>{selectedStatus.label}</span>}
      </section>

      {selectedProvider?.real_provider && (
        <section className="dock-section real-provider-authorization">
          <label className="real-provider-toggle">
            <input
              type="checkbox"
              checked={allowRealProvider}
              onChange={(event) => onAllowRealProviderChange(event.target.checked)}
              disabled={loading}
            />
            <span>Permitir uso real de {selectedProvider.label} e lembrar neste navegador</span>
          </label>
          <p className="safe-mode-copy">
            {allowRealProvider
              ? `Autorização salva neste navegador para ${selectedProvider.label}. Nenhuma chave é guardada aqui — as credenciais permanecem apenas no backend.`
              : "Safe Mode ativo: o envio fica bloqueado enquanto o uso real deste provider não for autorizado."}
          </p>
        </section>
      )}

      <section className="dock-section">
        <span className="dock-label">Modo de resposta</span>
        <div className="mode-tabs" role="group" aria-label="Modo de resposta">
          {MODE_OPTIONS.slice(0, 3).map((item) => (
            <button
              key={item.value}
              type="button"
              className={item.value === mode ? "active-mode" : ""}
              onClick={() => onModeChange(item.value)}
              disabled={loading}
              aria-pressed={item.value === mode}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="mode-description">{selectedMode.description}</p>
      </section>

      <section className="dock-section">
        <label htmlFor="settings-system-prompt">Prompt base</label>
        <textarea
          id="settings-system-prompt"
          value={systemPrompt}
          onChange={(event) => onSystemPromptChange(event.target.value)}
          disabled={loading}
          maxLength={2000}
        />
        <div className="prompt-toolbar">
          <span>{systemPrompt.length} / 2000</span>
          <button type="button" onClick={onResetPrompt} disabled={loading || systemPrompt === defaultSystemPrompt}>
            Restaurar
          </button>
        </div>
      </section>

      <section className="dock-section">
        <span className="dock-label">Diagnóstico local</span>
        <a className="observability-link" href="#/observability">
          Observabilidade QA/local
        </a>
      </section>

      {showInternalArea && (
        <section className="dock-section advanced-section">
          <span className="dock-label">Avançado — desenvolvimento</span>
          <p className="advanced-copy">
            Infraestrutura interna do pipeline, visível apenas na build de
            desenvolvimento. Não são IAs externas: as IAs ficam acima, em Provedores de
            IA. Só <code>mock</code> é um destino de conversa — responde a qualquer
            mensagem sem rede e sem chave. Os demais aparecem como referência e não são
            selecionáveis: <code>auto</code> é estratégia de roteamento,
            <code>local_qa</code> é análise determinística de artefatos e
            <code>local_model</code> exige opt-in que esta interface não envia.
          </p>
          <div className="internal-provider-list">
            {internalProviders.map((item) => {
              // Selecionável apenas o que o composer aceita de fato. Oferecer um
              // botão que leva a um envio bloqueado foi justamente a incoerência
              // corrigida nesta frente.
              const selectable = isDevProviderId(item.name);

              if (!selectable) {
                return (
                  <div key={item.name} className="internal-provider-note">
                    <strong>{item.label}</strong>
                    <small>{item.name}</small>
                    <em>não é destino de conversa</em>
                  </div>
                );
              }

              return (
                <button
                  key={item.name}
                  type="button"
                  className={item.name === provider ? "active-provider" : ""}
                  onClick={() => onProviderChange(item.name)}
                  disabled={loading}
                  aria-pressed={item.name === provider}
                >
                  <strong>{item.label}</strong>
                  <small>{item.name}</small>
                  <em>uso técnico</em>
                </button>
              );
            })}
          </div>
        </section>
      )}

      <section className="safety-note">
        <strong>Preferências salvas localmente</strong>
        <p>
          Provider, modelo, modo, prompt base e a autorização de uso real ficam somente neste
          navegador. Chaves de API nunca são gravadas aqui — permanecem exclusivamente no backend.
        </p>
      </section>

      <div className="settings-actions">
        <button className="secondary-button" type="button" onClick={onClose}>
          Fechar
        </button>
        <button className="primary-button" type="button" onClick={onSave}>
          Salvar configuração local
        </button>
      </div>
    </div>
  );
}
