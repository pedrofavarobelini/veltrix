import { describe, expect, it } from "vitest";
import {
  MAX_ATTACHMENTS,
  MAX_ATTACHMENT_BYTES,
  MAX_TOTAL_ATTACHMENT_BYTES,
  formatFileSize,
  getFileExtension,
  readTextAttachments,
  resolveArtifactType,
  sanitizeFileName,
  toArtifactInputs,
} from "./attachments";
import type { TextAttachment } from "./attachments";

/** Cria um `File` textual do tamanho pedido, em bytes ASCII. */
function makeFile(name: string, content: string, type = "text/plain"): File {
  return new File([content], name, { type });
}

function fill(bytes: number): string {
  return "a".repeat(bytes);
}

describe("saneamento de nome de arquivo", () => {
  it("descarta qualquer componente de caminho", () => {
    expect(sanitizeFileName("C:\\Users\\Pedro\\secreto\\notas.md")).toBe("notas.md");
    expect(sanitizeFileName("/etc/passwd.txt")).toBe("passwd.txt");
    expect(sanitizeFileName("../../../escape.txt")).toBe("escape.txt");
  });

  it("remove caracteres de controle", () => {
    expect(sanitizeFileName("re\u0000la\u001Ftorio.md")).toBe("relatorio.md");
  });

  it("nunca devolve string vazia", () => {
    expect(sanitizeFileName("   ")).toBe("arquivo-sem-nome");
    expect(sanitizeFileName("/")).toBe("arquivo-sem-nome");
  });
});

describe("allowlist de formatos", () => {
  it("aceita as extensões textuais e as mapeia para tipos do backend", () => {
    expect(resolveArtifactType("notas.txt")).toBe("text");
    expect(resolveArtifactType("README.md")).toBe("markdown");
    expect(resolveArtifactType("doc.markdown")).toBe("markdown");
    expect(resolveArtifactType("dados.csv")).toBe("text");
    expect(resolveArtifactType("saida.json")).toBe("json_result");
    expect(resolveArtifactType("app.log")).toBe("log");
  });

  it("recusa formatos fora da allowlist", () => {
    for (const name of ["foto.png", "doc.pdf", "planilha.xlsx", "script.exe", "app.js"]) {
      expect(resolveArtifactType(name)).toBeNull();
    }
  });

  it("não se deixa enganar por extensão dupla", () => {
    expect(resolveArtifactType("relatorio.md.exe")).toBeNull();
    expect(getFileExtension("relatorio.md.exe")).toBe(".exe");
  });

  it("ignora diferença de caixa na extensão", () => {
    expect(resolveArtifactType("LEIAME.MD")).toBe("markdown");
  });
});

describe("leitura e validação de anexos", () => {
  it("aceita um arquivo textual válido e lê o conteúdo", async () => {
    const result = await readTextAttachments([makeFile("notas.md", "# Título")]);

    expect(result.rejected).toHaveLength(0);
    expect(result.accepted).toHaveLength(1);
    expect(result.accepted[0].name).toBe("notas.md");
    expect(result.accepted[0].artifactType).toBe("markdown");
    expect(result.accepted[0].content).toBe("# Título");
  });

  it("rejeita extensão não permitida", async () => {
    const result = await readTextAttachments([makeFile("foto.png", "conteudo", "image/png")]);

    expect(result.accepted).toHaveLength(0);
    expect(result.rejected[0].reason).toContain("Formato não suportado");
  });

  it("rejeita arquivo vazio", async () => {
    const result = await readTextAttachments([makeFile("vazio.txt", "")]);

    expect(result.accepted).toHaveLength(0);
    expect(result.rejected[0].reason).toBe("Arquivo vazio.");
  });

  it("rejeita arquivo só com espaços em branco", async () => {
    const result = await readTextAttachments([makeFile("branco.txt", "   \n\t  ")]);

    expect(result.accepted).toHaveLength(0);
    expect(result.rejected[0].reason).toBe("Arquivo sem conteúdo textual.");
  });

  it("rejeita arquivo acima do limite individual", async () => {
    const result = await readTextAttachments([
      makeFile("grande.txt", fill(MAX_ATTACHMENT_BYTES + 1)),
    ]);

    expect(result.accepted).toHaveLength(0);
    expect(result.rejected[0].reason).toContain("acima do limite");
  });

  it("aceita arquivo exatamente no limite individual", async () => {
    const result = await readTextAttachments([
      makeFile("limite.txt", fill(MAX_ATTACHMENT_BYTES)),
    ]);

    expect(result.accepted).toHaveLength(1);
  });

  it("rejeita MIME incoerente mesmo com extensão permitida", async () => {
    const result = await readTextAttachments([
      makeFile("disfarce.txt", "conteudo", "application/octet-stream"),
    ]);

    expect(result.accepted).toHaveLength(0);
    expect(result.rejected[0].reason).toContain("não textual");
  });

  it("aceita MIME vazio, que é o que o navegador informa quando não sabe", async () => {
    const result = await readTextAttachments([makeFile("sem-mime.log", "linha", "")]);

    expect(result.accepted).toHaveLength(1);
  });

  it("respeita o limite de quantidade contando os anexos já presentes", async () => {
    const existing: TextAttachment[] = Array.from({ length: MAX_ATTACHMENTS }, (_, index) => ({
      id: `existente-${index}`,
      name: `a${index}.txt`,
      size: 10,
      artifactType: "text",
      content: "x",
    }));

    const result = await readTextAttachments([makeFile("extra.txt", "conteudo")], existing);

    expect(result.accepted).toHaveLength(0);
    expect(result.rejected[0].reason).toContain(`Limite de ${MAX_ATTACHMENTS} anexos`);
  });

  it("respeita a cota total somando os anexos já presentes", async () => {
    const existing: TextAttachment[] = [
      {
        id: "existente",
        name: "grande.txt",
        size: MAX_TOTAL_ATTACHMENT_BYTES - 100,
        artifactType: "text",
        content: "x",
      },
    ];

    const result = await readTextAttachments([makeFile("mais.txt", fill(500))], existing);

    expect(result.accepted).toHaveLength(0);
    expect(result.rejected[0].reason).toContain("Total de anexos");
  });

  it("decide arquivo a arquivo: um recusado não derruba os válidos da mesma seleção", async () => {
    const result = await readTextAttachments([
      makeFile("bom.md", "# ok"),
      makeFile("ruim.png", "x", "image/png"),
      makeFile("outro.log", "linha"),
    ]);

    expect(result.accepted.map((item) => item.name)).toEqual(["bom.md", "outro.log"]);
    expect(result.rejected.map((item) => item.name)).toEqual(["ruim.png"]);
  });

  it("mantém os limites do frontend abaixo dos do backend, evitando truncamento silencioso", () => {
    // Backend: MAX_ARTIFACTS=10, MAX_ARTIFACT_CONTENT_CHARS=20000,
    // MAX_TOTAL_ARTIFACT_CHARS=100000. Em UTF-8, chars <= bytes.
    expect(MAX_ATTACHMENTS).toBeLessThanOrEqual(10);
    expect(MAX_ATTACHMENT_BYTES).toBeLessThanOrEqual(20000);
    expect(MAX_TOTAL_ATTACHMENT_BYTES).toBeLessThan(100000);
    expect(MAX_ATTACHMENTS * MAX_ATTACHMENT_BYTES).toBeLessThanOrEqual(100000);
  });
});

describe("payload enviado ao /api/chat", () => {
  it("envia tipo, nome e conteúdo, e nunca metadata de caminho", () => {
    const payload = toArtifactInputs([
      { id: "1", name: "notas.md", size: 8, artifactType: "markdown", content: "# Título" },
    ]);

    expect(payload).toEqual([{ type: "markdown", name: "notas.md", content: "# Título" }]);
    expect(payload[0]).not.toHaveProperty("metadata");
    expect(Object.keys(payload[0])).not.toContain("path");
    expect(Object.keys(payload[0])).not.toContain("file_path");
  });
});

describe("formatação de tamanho", () => {
  it("usa bytes abaixo de 1 KB e KB acima", () => {
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(2048)).toBe("2.0 KB");
    expect(formatFileSize(20000)).toBe("20 KB");
  });
});
