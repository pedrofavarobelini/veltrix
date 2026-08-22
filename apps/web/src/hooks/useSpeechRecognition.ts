/**
 * Ditado por voz do composer (PEDROCORE-V1-FINAL-CLOSURE).
 *
 * O QUE ESTE HOOK NÃO FAZ, por decisão de projeto:
 *
 *   - não grava áudio;
 *   - não guarda áudio em memória, `localStorage` ou qualquer lugar;
 *   - não envia áudio ao backend do PedroCore;
 *   - não envia áudio a nenhum provider;
 *   - não registra áudio em log.
 *
 * O hook recebe do navegador apenas TEXTO já transcrito e o entrega ao
 * chamador. O áudio nunca passa por código nosso.
 *
 * HONESTIDADE SOBRE A TRANSCRIÇÃO — a Web Speech API é uma interface, não uma
 * promessa de implementação. O navegador decide como reconhece a fala, e
 * vários (Chrome e Edge entre eles) fazem isso enviando o áudio a um serviço
 * de nuvem do próprio fornecedor. Portanto: esta transcrição NÃO é
 * necessariamente offline e não pode ser apresentada como tal ao usuário. A
 * interface diz isso explicitamente, e o suporte é detectado em tempo de
 * execução em vez de presumido.
 */

import { useCallback, useEffect, useRef, useState } from "react";

/** Estado observável do ditado. `unsupported` é terminal para a sessão. */
export type SpeechRecognitionStatus =
  | "unsupported"
  | "idle"
  | "listening"
  | "denied"
  | "error";

/** Superfície mínima da Web Speech API que de fato usamos. */
type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<
    ArrayLike<{ transcript: string }> & { isFinal: boolean }
  >;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

type SpeechCapableWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

/**
 * Resolve o construtor disponível, na ordem padronizado → prefixado.
 *
 * O prefixo `webkit` continua sendo o único caminho em navegadores baseados
 * em Chromium, então ele não é legado: é o caso mais comum na prática.
 */
export function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") {
    return null;
  }

  const candidate = window as SpeechCapableWindow;

  return candidate.SpeechRecognition ?? candidate.webkitSpeechRecognition ?? null;
}

export const DEFAULT_SPEECH_LANGUAGE = "pt-BR";

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Permissão de microfone negada pelo navegador.",
  "service-not-allowed": "Permissão de microfone negada pelo navegador.",
  "no-speech": "Nenhuma fala detectada. Tente novamente.",
  "audio-capture": "Nenhum microfone disponível.",
  network: "Falha de rede no serviço de transcrição do navegador.",
  aborted: "",
};

const DENIED_ERRORS = new Set(["not-allowed", "service-not-allowed"]);

type UseSpeechRecognitionOptions = {
  /** Idioma do reconhecimento. */
  lang?: string;
  /** Recebe cada trecho FINAL transcrito. Nunca recebe áudio. */
  onTranscript: (text: string) => void;
};

/**
 * Ditado com ciclo de vida explícito: iniciar, parar (mantendo o que foi dito)
 * e cancelar (descartando).
 *
 * O texto vai para o textarea e para por aí — nada é enviado automaticamente.
 * Quem revisa e decide enviar é sempre o usuário.
 */
export function useSpeechRecognition({
  lang = DEFAULT_SPEECH_LANGUAGE,
  onTranscript,
}: UseSpeechRecognitionOptions) {
  const [status, setStatus] = useState<SpeechRecognitionStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // O callback fica em ref para que trocar de identidade a cada render do pai
  // não obrigue a recriar o reconhecimento no meio de uma fala.
  const onTranscriptRef = useRef(onTranscript);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  // Detecção acontece no efeito, não no corpo: `window` pode não existir na
  // primeira avaliação e o suporte não muda durante a sessão.
  useEffect(() => {
    if (getSpeechRecognitionConstructor() === null) {
      setStatus("unsupported");
    }
  }, []);

  // Encerra qualquer reconhecimento vivo ao desmontar: sem isso o navegador
  // seguiria com o microfone aberto depois que o componente saiu da tela.
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    };
  }, []);

  const supported = status !== "unsupported";

  const start = useCallback(() => {
    const Constructor = getSpeechRecognitionConstructor();

    if (Constructor === null) {
      setStatus("unsupported");
      return;
    }

    if (recognitionRef.current !== null) {
      return;
    }

    const recognition = new Constructor();

    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      // Só trechos FINAIS entram no textarea. Resultado interino muda sozinho
      // e reescreveria o que o usuário já estivesse editando.
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];

        if (result?.isFinal) {
          const transcript = result[0]?.transcript ?? "";

          if (transcript.trim()) {
            onTranscriptRef.current(transcript.trim());
          }
        }
      }
    };

    recognition.onerror = (event) => {
      const code = event.error ?? "unknown";
      const message = ERROR_MESSAGES[code] ?? "Não foi possível transcrever o áudio.";

      recognitionRef.current = null;

      if (DENIED_ERRORS.has(code)) {
        setStatus("denied");
        setErrorMessage(message);
        return;
      }

      // `aborted` é o cancelamento pedido pelo próprio usuário: volta ao
      // repouso em silêncio, sem apresentar um erro que ele mesmo causou.
      if (code === "aborted") {
        setStatus("idle");
        setErrorMessage("");
        return;
      }

      setStatus("error");
      setErrorMessage(message);
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      // `onerror` já definiu um estado terminal quando houve falha; sobrescrever
      // aqui apagaria o motivo antes de o usuário conseguir lê-lo.
      setStatus((current) => (current === "listening" ? "idle" : current));
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      setErrorMessage("");
      setStatus("listening");
    } catch {
      recognitionRef.current = null;
      setStatus("error");
      setErrorMessage("Não foi possível iniciar o microfone.");
    }
  }, [lang]);

  /** Encerra mantendo o que já foi transcrito. */
  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setStatus((current) => (current === "listening" ? "idle" : current));
  }, []);

  /** Encerra descartando o trecho em andamento. */
  const cancel = useCallback(() => {
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    setStatus((current) => (current === "listening" ? "idle" : current));
    setErrorMessage("");
  }, []);

  return { supported, status, errorMessage, start, stop, cancel };
}
