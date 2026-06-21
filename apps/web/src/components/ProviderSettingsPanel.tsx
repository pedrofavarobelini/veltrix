import mockLogo from "../assets/providers/mock.svg";
import geminiLogo from "../assets/providers/gemini.svg";
import openaiLogo from "../assets/providers/openai.svg";
import claudeLogo from "../assets/providers/claude.svg";
import deepseekLogo from "../assets/providers/deepseek.svg";
import grokLogo from "../assets/providers/grok.svg";
import type { RefObject } from "react";
import type { ProviderInfo } from "../services/api";

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
  panelRef?: RefObject<HTMLElement | null>;
  providers: ProviderInfo[];
  provider: string;
  model: string;
  mode: string;
  systemPrompt: string;
  defaultSystemPrompt: string;
  loading: boolean;
  onProviderChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onModeChange: (value: string) => void;
  onSystemPromptChange: (value: string) => void;
  onResetModel: () => void;
  onResetPrompt: () => void;
  onClose: () => void;
  onSave: () => void;
};

function getProviderStatus(provider: ProviderInfo) {
  if (!provider.real_provider) {
    return {
      label: "Mock local",
      description: "Provider seguro para testes sem chave externa.",
      className: "status-mock",
    };
  }

  if (provider.configured) {
    return {
      label: "Configurado",
      description: "Chave detectada no .env local do backend.",
      className: "status-ok",
    };
  }

  return {
    label: "Sem chave",
    description: "O backend pode acionar fallback para MockProvider.",
    className: "status-warning",
  };
}

export function ProviderSettingsPanel({
  panelRef,
  providers,
  provider,
  model,
  mode,
  systemPrompt,
  defaultSystemPrompt,
  loading,
  onProviderChange,
  onModelChange,
  onModeChange,
  onSystemPromptChange,
  onResetModel,
  onResetPrompt,
  onClose,
  onSave,
}: ProviderSettingsPanelProps) {
  const selectedProvider = providers.find((item) => item.name === provider) ?? providers[0];
  const selectedStatus = selectedProvider ? getProviderStatus(selectedProvider) : null;
  const selectedMode = MODE_OPTIONS.find((item) => item.value === mode) ?? MODE_OPTIONS[0];

  return (
    <aside ref={panelRef} className="provider-dock" aria-label="Configuração de provider do PedroCore IA">
      <div className="dock-header">
        <span className="dock-kicker">Configuração do provider</span>
        <h2>Provedores de IA</h2>
        <p>Gerencie seus providers sem expor chaves no frontend.</p>
      </div>

      <section className="provider-card-grid" aria-label="Providers disponíveis">
        {providers.map((item) => {
          const status = getProviderStatus(item);
          const active = item.name === provider;

          return (
            <button
              className={`provider-card-option ${active ? "active-provider" : ""}`}
              type="button"
              key={item.name}
              onClick={() => onProviderChange(item.name)}
              disabled={loading}
            >
              <span className="provider-icon">
                {PROVIDER_ICONS[item.name] ? (
                  <img src={PROVIDER_ICONS[item.name]} alt={`${item.label} logo`} />
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
      </section>

      <section className="dock-section">
        <label>
          Modelo
          <div className="inline-field-action">
            <input value={model} onChange={(event) => onModelChange(event.target.value)} disabled={loading} />
            <button type="button" onClick={onResetModel} disabled={loading || !selectedProvider}>
              Padrão
            </button>
          </div>
        </label>
        {selectedStatus && <span className={`provider-status ${selectedStatus.className}`}>{selectedStatus.label}</span>}
      </section>

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
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="mode-description">{selectedMode.description}</p>
      </section>

      <section className="dock-section">
        <label>
          Prompt base
          <textarea
            value={systemPrompt}
            onChange={(event) => onSystemPromptChange(event.target.value)}
            disabled={loading}
            maxLength={2000}
          />
        </label>
        <div className="prompt-toolbar">
          <span>{systemPrompt.length} / 2000</span>
          <button type="button" onClick={onResetPrompt} disabled={loading || systemPrompt === defaultSystemPrompt}>
            Restaurar
          </button>
        </div>
      </section>

      <section className="safety-note">
        <strong>Configurações salvas localmente</strong>
        <p>Somente neste navegador/dispositivo. Chaves continuam exclusivamente no backend.</p>
      </section>

      <div className="settings-actions">
        <button className="secondary-button" type="button" onClick={onClose}>
          Sincronizar local
        </button>
        <button className="primary-button" type="button" onClick={onSave}>
          Salvar configuração local
        </button>
      </div>
    </aside>
  );
}
