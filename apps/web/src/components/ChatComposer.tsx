import { useCallback, useLayoutEffect, useRef } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";
import type { ProviderInfo } from "../services/api";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { ACCEPTED_FILE_EXTENSIONS, MAX_ATTACHMENTS, formatFileSize } from "../utils/attachments";
import type { TextAttachment } from "../utils/attachments";
import { describeUnavailability, isSelectableProvider } from "../utils/publicProviders";

/** Teto de crescimento do textarea; acima disso ele rola em vez de empurrar o chat. */
const MAX_TEXTAREA_HEIGHT = 200;

const SELECT_PROVIDER_LABEL = "Selecionar IA";

const MIC_LABELS = {
  start: "Ditar mensagem por voz",
  stop: "Parar ditado e manter o texto",
  cancel: "Cancelar ditado e descartar",
  unsupported: "Ditado por voz indisponível neste navegador",
};

const MIC_HINT =
  "Ouvindo. A transcrição é feita pelo navegador e pode ser processada por um serviço do fornecedor dele; o áudio não é gravado nem enviado ao Veltrix.";

type ChatComposerProps = {
  value: string;
  loading: boolean;
  placeholder: string;
  /**
   * IAs públicas conhecidas — configuradas ou não. As indisponíveis aparecem
   * desabilitadas e explicadas, em vez de sumirem da lista. Em desenvolvimento
   * inclui também os internos aptos a chat.
   */
  offeredProviders: ProviderInfo[];
  provider: string;
  /** `true` quando `provider` é oferecível — só aí o seletor mostra um nome. */
  providerIsSelectable: boolean;
  /** `true` quando o provider ativo é interno, liberado apenas em desenvolvimento. */
  providerIsDev: boolean;
  /** Motivo visível do bloqueio; string vazia quando o envio está liberado. */
  notice: string;
  /** Regras do pai (loading, provider ausente, autorização faltando). */
  canSend: boolean;
  /** Anexos textuais já validados e lidos. */
  attachments: TextAttachment[];
  onChange: (value: string) => void;
  onProviderChange: (value: string) => void;
  onSend: () => void;
  onAttachmentsSelected: (files: File[]) => void;
  onAttachmentRemove: (id: string) => void;
};

export function ChatComposer({
  value,
  loading,
  placeholder,
  offeredProviders,
  provider,
  providerIsSelectable,
  providerIsDev,
  notice,
  canSend,
  attachments,
  onChange,
  onProviderChange,
  onSend,
  onAttachmentsSelected,
  onAttachmentRemove,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  // O valor atual em ref: o hook de voz é criado uma vez e não deve recriar o
  // reconhecimento a cada tecla digitada só para enxergar o texto mais novo.
  const valueRef = useRef(value);

  valueRef.current = value;

  // A transcrição é ANEXADA ao que já existe, nunca substitui: o usuário pode
  // ter digitado antes de falar, e perder isso seria destrutivo.
  const handleTranscript = useCallback(
    (text: string) => {
      const current = valueRef.current;
      const separator = current && !current.endsWith(" ") ? " " : "";

      onChange(`${current}${separator}${text}`);
    },
    [onChange],
  );

  const speech = useSpeechRecognition({ onTranscript: handleTranscript });
  const listening = speech.status === "listening";

  // O textarea cresce com o conteúdo: zeramos a altura para que `scrollHeight`
  // volte a medir o texto real, e então aplicamos o menor valor entre ele e o teto.
  useLayoutEffect(() => {
    const element = textareaRef.current;

    if (!element) {
      return;
    }

    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [value]);

  // Uma mensagem só de anexos é legítima: "analise este log" pode estar no
  // arquivo. O que não pode é enviar absolutamente nada.
  const isEmpty = value.trim().length === 0 && attachments.length === 0;
  const sendDisabled = !canSend || isEmpty;
  const attachmentsFull = attachments.length >= MAX_ATTACHMENTS;

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter envia; Shift+Enter cai no comportamento nativo e quebra a linha.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      if (!sendDisabled) {
        onSend();
      }
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);

    if (files.length > 0) {
      onAttachmentsSelected(files);
    }

    // Zerar o input permite reescolher o MESMO arquivo depois de removê-lo —
    // sem isso o navegador não dispara `change` para um valor idêntico.
    event.target.value = "";
  }

  return (
    <footer className="chat-composer">
      {notice && (
        <p className="composer-notice" role="status">
          {notice}
        </p>
      )}

      {listening && (
        <p className="composer-notice composer-listening" role="status">
          {MIC_HINT}
        </p>
      )}

      {speech.errorMessage && (
        <p className="composer-notice composer-mic-error" role="alert">
          {speech.errorMessage}
        </p>
      )}

      <label className="sr-only" htmlFor="composer-message">
        Mensagem para o Veltrix
      </label>
      <textarea
        id="composer-message"
        ref={textareaRef}
        className="composer-textarea"
        value={value}
        rows={1}
        placeholder={placeholder}
        disabled={loading}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />

      {attachments.length > 0 && (
        <ul className="composer-attachments" aria-label="Anexos desta mensagem">
          {attachments.map((item) => (
            <li key={item.id} className="attachment-chip">
              <span className="attachment-name" title={item.name}>
                {item.name}
              </span>
              <span className="attachment-size">{formatFileSize(item.size)}</span>
              <span className="attachment-type">{item.artifactType}</span>
              <button
                type="button"
                className="attachment-remove"
                onClick={() => onAttachmentRemove(item.id)}
                disabled={loading}
                aria-label={`Remover anexo ${item.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="composer-toolbar">
        <div className="composer-actions">
          <input
            ref={fileInputRef}
            id="composer-attachment-input"
            className="sr-only"
            type="file"
            multiple
            accept={ACCEPTED_FILE_EXTENSIONS}
            onChange={handleFileChange}
            disabled={loading || attachmentsFull}
          />
          <button
            type="button"
            className="composer-icon-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading || attachmentsFull}
            aria-label={
              attachmentsFull
                ? `Limite de ${MAX_ATTACHMENTS} anexos atingido`
                : "Anexar arquivo de texto"
            }
            title={
              attachmentsFull
                ? `Limite de ${MAX_ATTACHMENTS} anexos atingido`
                : "Anexar arquivo de texto"
            }
          >
            <span aria-hidden="true">+</span>
          </button>

          {/* Sem suporte no navegador o botão fica desabilitado e explica o
              porquê, em vez de aparecer funcional e não fazer nada. */}
          <button
            type="button"
            className={`composer-icon-button ${listening ? "is-listening" : ""}`}
            onClick={listening ? speech.stop : speech.start}
            disabled={loading || !speech.supported}
            aria-pressed={listening}
            aria-label={
              speech.supported ? (listening ? MIC_LABELS.stop : MIC_LABELS.start) : MIC_LABELS.unsupported
            }
            title={
              speech.supported ? (listening ? MIC_LABELS.stop : MIC_LABELS.start) : MIC_LABELS.unsupported
            }
          >
            <span aria-hidden="true">🎙</span>
          </button>

          {listening && (
            <button
              type="button"
              className="composer-cancel-mic"
              onClick={speech.cancel}
              aria-label={MIC_LABELS.cancel}
            >
              Cancelar
            </button>
          )}
        </div>

        {/* Seletor e Enviar formam um grupo à direita: escolher a IA e mandar a
            mensagem são a mesma decisão, e separá-los deixava um vão morto. */}
        <div className="composer-send-group">
          <div className="composer-provider">
            <label className="sr-only" htmlFor="composer-provider">
              IA utilizada nesta conversa
            </label>
            {/* Rótulo de ambiente técnico: um provider interno nunca deve passar
                por IA pública, mesmo em desenvolvimento. */}
            {providerIsDev && <span className="composer-dev-badge">DEV</span>}
            <select
              id="composer-provider"
              className="composer-provider-select"
              value={providerIsSelectable ? provider : ""}
              disabled={loading}
              onChange={(event) => onProviderChange(event.target.value)}
            >
              <option value="" disabled>
                {SELECT_PROVIDER_LABEL}
              </option>
              {offeredProviders.map((item) => {
                // IA conhecida mas indisponível continua VISÍVEL e desabilitada,
                // com o motivo no próprio rótulo. Some da lista seria pior: o
                // usuário não saberia que ela existe, nem o que fazer para
                // habilitá-la.
                const unavailability = describeUnavailability(item);

                return (
                  <option
                    key={item.name}
                    value={item.name}
                    disabled={!isSelectableProvider(item)}
                  >
                    {unavailability ? `${item.label} — ${unavailability}` : item.label}
                  </option>
                );
              })}
            </select>
          </div>

          <button className="send-button" type="button" onClick={onSend} disabled={sendDisabled}>
            {loading ? "Enviando..." : "Enviar"}
          </button>
        </div>
      </div>
    </footer>
  );
}
