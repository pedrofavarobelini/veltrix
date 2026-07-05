import json

from app.modules.prompt_builder.schemas import PromptBuildInput, PromptBuildResult

DEFAULT_SYSTEM_PROMPT = (
    "Você é o PedroCore IA, um assistente pessoal técnico, claro, direto e útil."
)

FINGUARD_SECURITY_RULE = (
    "O FinGuard é um projeto externo e somente leitura; não altere nada nele."
)

BASE_SECURITY_RULES = [
    "Não executar comandos.",
    "Não alterar arquivos.",
    "Não tratar respostas Mock/fallback como validação real em tarefas críticas.",
]


class PromptBuilder:
    def build(self, data: PromptBuildInput) -> PromptBuildResult:
        base_prompt = data.system_prompt or DEFAULT_SYSTEM_PROMPT

        security_rules = list(BASE_SECURITY_RULES)
        if data.project.project_id == "finguard":
            security_rules.append(FINGUARD_SECURITY_RULE)

        context_text = (
            json.dumps(data.context, ensure_ascii=False)
            if data.context
            else "Nenhum contexto adicional foi enviado."
        )
        metadata_text = (
            json.dumps(data.metadata, ensure_ascii=False)
            if data.metadata
            else "Nenhuma metadata adicional foi enviada."
        )

        sections = [
            f"[Instruções do sistema]\n{base_prompt}",
            (
                "[Tarefa]\n"
                f"task_type: {data.strategy.task_type}\n"
                f"response_style: {data.strategy.response_style}\n"
                f"criticality: {data.strategy.criticality}\n"
                f"requires_structured_response: {data.strategy.requires_structured_response}"
            ),
            (
                "[Origem]\n"
                f"origin_system: {data.origin_system}\n"
                f"project_id: {data.project.project_id}\n"
                f"display_name: {data.project.display_name}"
            ),
            (
                "[Limites do projeto]\n"
                f"read_only: {data.project.read_only}\n"
                f"can_execute_commands: {data.project.can_execute_commands}\n"
                f"can_write_files: {data.project.can_write_files}"
            ),
            f"[Contexto enviado]\n{context_text}",
            f"[Metadata]\n{metadata_text}",
            f"[Artefatos enviados]\n{data.artifacts_text_block or 'Nenhum artefato foi enviado.'}",
            "[Regras de segurança]\n" + "\n".join(f"- {rule}" for rule in security_rules),
        ]

        enriched_system_prompt = "\n\n".join(sections)
        full_prompt = f"{enriched_system_prompt}\n\n[Mensagem do usuário]\n{data.message}"

        return PromptBuildResult(
            enriched_system_prompt=enriched_system_prompt,
            full_prompt=full_prompt,
        )


prompt_builder = PromptBuilder()
