/**
 * Anexos TEXTUAIS do composer (PEDROCORE-V1-FINAL-CLOSURE).
 *
 * Não existe endpoint novo e nenhum upload binário. Um anexo aqui é lido no
 * navegador com a File API e enviado como `ArtifactInput` no campo `artifacts`
 * que o `/api/chat` já aceita desde a frente de artefatos — o mesmo contrato
 * que FinGuard e Structa usam. O backend permanece intocado.
 *
 * LIMITES — a escolha não é arbitrária, ela espelha
 * `apps/api/app/modules/artifacts/service.py`:
 *
 *   backend  MAX_ARTIFACTS = 10, MAX_ARTIFACT_CONTENT_CHARS = 20000,
 *            MAX_TOTAL_ARTIFACT_CHARS = 100000 — e o que passa disso é
 *            TRUNCADO com warning, não rejeitado.
 *
 * Truncar em silêncio é pior do que recusar: o usuário veria o arquivo aceito
 * e a IA responderia sobre metade dele. Por isso os limites daqui ficam
 * estritamente ABAIXO dos do backend, e a checagem é feita em BYTES antes da
 * leitura. Em UTF-8 todo caractere ocupa pelo menos um byte, logo
 * `bytes <= 20000` garante `chars <= 20000` — o teto exato por artefato do
 * backend — sem precisar ler o arquivo para descobrir.
 */

/** Um anexo já validado e lido, pronto para virar `ArtifactInput`. */
export type TextAttachment = {
  /** Identificador local, usado só como `key` de render e para remoção. */
  id: string;
  /** Nome saneado do arquivo. É METADADO: nunca vira caminho nem é lido do disco. */
  name: string;
  /** Tamanho original em bytes, para exibição. */
  size: number;
  /** Tipo de artefato do contrato do backend (não o MIME do navegador). */
  artifactType: string;
  /** Conteúdo textual lido no navegador. */
  content: string;
};

export type AttachmentRejection = {
  /** Nome saneado do arquivo recusado. */
  name: string;
  /** Motivo legível, já pronto para a interface. */
  reason: string;
};

export type AttachmentSelectionResult = {
  accepted: TextAttachment[];
  rejected: AttachmentRejection[];
};

/** Quantidade máxima de anexos por mensagem (backend aceita 10). */
export const MAX_ATTACHMENTS = 4;

/**
 * Teto por arquivo, em bytes. Igual ao teto de CARACTERES por artefato do
 * backend: em UTF-8, `chars <= bytes`, então nada é truncado lá.
 */
export const MAX_ATTACHMENT_BYTES = 20000;

/** Teto somado. Fica bem abaixo dos 100000 caracteres totais do backend. */
export const MAX_TOTAL_ATTACHMENT_BYTES = 60000;

/**
 * Allowlist explícita por EXTENSÃO, mapeada para os tipos que
 * `TEXT_ARTIFACT_TYPES` do backend já reconhece. Um tipo fora dessa lista
 * geraria `ARTIFACT_TYPE_UNKNOWN`; por isso `.csv` entra como `text` e não
 * como um tipo inventado.
 *
 * A extensão é a autoridade, não o MIME: `File.type` vem do sistema
 * operacional, é facilmente vazio (`""`) e não é confiável como controle de
 * segurança. O MIME só é usado como sinal adicional em `isTrustworthyMime`.
 */
export const ALLOWED_ATTACHMENT_TYPES: Record<string, string> = {
  ".txt": "text",
  ".md": "markdown",
  ".markdown": "markdown",
  ".csv": "text",
  ".json": "json_result",
  ".log": "log",
};

/** Extensões aceitas, no formato que o atributo `accept` do input espera. */
export const ACCEPTED_FILE_EXTENSIONS = Object.keys(ALLOWED_ATTACHMENT_TYPES).join(",");

/** MIMEs coerentes com a allowlist. Ausente ou desconhecido não reprova nada. */
const TEXTUAL_MIME_PREFIXES = ["text/"];
const TEXTUAL_MIME_EXACT = new Set([
  "application/json",
  "application/csv",
  "application/x-ndjson",
  "",
]);

/**
 * Saneia o nome para uso como METADADO e como texto de interface.
 *
 * Remove qualquer componente de diretório (`/`, `\`) — um `name` de `<input
 * type="file">` não deveria trazer caminho, mas o valor vem do cliente e é
 * tratado como não confiável. Também remove caracteres de controle, que não
 * têm representação visual e poluiriam log e interface.
 *
 * O resultado NUNCA é usado para abrir, resolver ou construir caminho algum:
 * o conteúdo já foi lido pela File API a partir do objeto `File`.
 */
export function sanitizeFileName(rawName: string): string {
  const withoutPath = rawName.split(/[\\/]/).pop() ?? "";
  // Faixa de controle C0 mais DEL, escrita com escapes explicitos.
  const withoutControlChars = withoutPath.replace(/[\u0000-\u001F\u007F]/g, "");
  const trimmed = withoutControlChars.trim();

  if (!trimmed) {
    return "arquivo-sem-nome";
  }

  return trimmed.length > 120 ? `${trimmed.slice(0, 117)}...` : trimmed;
}

/** Extensão em minúsculas, com ponto. String vazia quando não há extensão. */
export function getFileExtension(fileName: string): string {
  const dotIndex = fileName.lastIndexOf(".");

  if (dotIndex <= 0 || dotIndex === fileName.length - 1) {
    return "";
  }

  return fileName.slice(dotIndex).toLowerCase();
}

/** Tipo de artefato para a extensão, ou `null` quando ela não é permitida. */
export function resolveArtifactType(fileName: string): string | null {
  return ALLOWED_ATTACHMENT_TYPES[getFileExtension(fileName)] ?? null;
}

/**
 * MIME coerente com um arquivo textual?
 *
 * Só é consultado quando o navegador informa algo. Vazio conta como
 * confiável porque é o valor que o próprio navegador usa quando não sabe — e
 * a extensão já validou o arquivo.
 */
export function isTrustworthyMime(mime: string): boolean {
  const normalized = mime.trim().toLowerCase();

  return (
    TEXTUAL_MIME_EXACT.has(normalized) ||
    TEXTUAL_MIME_PREFIXES.some((prefix) => normalized.startsWith(prefix))
  );
}

/** Formata bytes para a interface, sem casas decimais desnecessárias. */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kilobytes = bytes / 1024;

  return `${kilobytes >= 10 ? Math.round(kilobytes) : kilobytes.toFixed(1)} KB`;
}

function createAttachmentId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `attachment-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * Valida e lê os arquivos escolhidos, respeitando os anexos JÁ presentes.
 *
 * Cada arquivo é decidido de forma independente: um recusado não invalida os
 * demais, e a interface consegue dizer exatamente o que caiu e por quê. A
 * ordem das checagens é deliberada — as baratas (extensão, tamanho, cota)
 * vêm antes da leitura, para que um arquivo inaceitável nunca chegue a ser
 * carregado na memória.
 */
export async function readTextAttachments(
  files: File[],
  existing: TextAttachment[] = [],
): Promise<AttachmentSelectionResult> {
  const accepted: TextAttachment[] = [];
  const rejected: AttachmentRejection[] = [];

  let count = existing.length;
  let totalBytes = existing.reduce((sum, item) => sum + item.size, 0);

  for (const file of files) {
    const name = sanitizeFileName(file.name);

    if (count >= MAX_ATTACHMENTS) {
      rejected.push({
        name,
        reason: `Limite de ${MAX_ATTACHMENTS} anexos por mensagem atingido.`,
      });
      continue;
    }

    const artifactType = resolveArtifactType(name);

    if (artifactType === null) {
      rejected.push({
        name,
        reason: `Formato não suportado. Aceitos: ${Object.keys(ALLOWED_ATTACHMENT_TYPES).join(", ")}.`,
      });
      continue;
    }

    if (!isTrustworthyMime(file.type)) {
      rejected.push({ name, reason: "O navegador identificou este arquivo como não textual." });
      continue;
    }

    if (file.size === 0) {
      rejected.push({ name, reason: "Arquivo vazio." });
      continue;
    }

    if (file.size > MAX_ATTACHMENT_BYTES) {
      rejected.push({
        name,
        reason: `Arquivo acima do limite de ${formatFileSize(MAX_ATTACHMENT_BYTES)}.`,
      });
      continue;
    }

    if (totalBytes + file.size > MAX_TOTAL_ATTACHMENT_BYTES) {
      rejected.push({
        name,
        reason: `Total de anexos passaria de ${formatFileSize(MAX_TOTAL_ATTACHMENT_BYTES)}.`,
      });
      continue;
    }

    let content: string;

    try {
      content = await file.text();
    } catch {
      rejected.push({ name, reason: "Não foi possível ler o arquivo." });
      continue;
    }

    if (!content.trim()) {
      rejected.push({ name, reason: "Arquivo sem conteúdo textual." });
      continue;
    }

    accepted.push({
      id: createAttachmentId(),
      name,
      size: file.size,
      artifactType,
      content,
    });

    count += 1;
    totalBytes += file.size;
  }

  return { accepted, rejected };
}

/**
 * Converte anexos no payload `artifacts` do `/api/chat`.
 *
 * `metadata` fica deliberadamente AUSENTE. O backend rejeita o artefato
 * inteiro quando encontra chave de caminho (`path`, `file_path`, `directory`,
 * …) em `PATH_LIKE_METADATA_KEYS`, e não há nada aqui que precise viajar
 * além de nome e conteúdo. Nome vai em `name`, como metadado puro.
 */
export function toArtifactInputs(attachments: TextAttachment[]) {
  return attachments.map((item) => ({
    type: item.artifactType,
    name: item.name,
    content: item.content,
  }));
}
