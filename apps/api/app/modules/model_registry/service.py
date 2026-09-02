"""Servico do Model Registry. Promocao exige evidencia; rollback e garantido."""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.model_registry.schemas import (
    ModelCapability,
    ModelEntry,
    ModelStatus,
    ModelTransition,
    requires_evidence,
    transition_allowed,
)


class ModelRegistryError(RuntimeError):
    """Recusa explicita do registry. Nunca silenciosa."""


class ModelRegistryService:
    """Registro em memoria com a forma de um repositorio durável.

    A durabilidade real e do Evidence Platform, que ja e durável: aqui ficam o
    estado corrente e a historia de transicoes, e cada promocao aponta para a
    evidencia que a sustenta.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ModelEntry] = {}
        self._history: list[ModelTransition] = []
        self._repository = None
        self._loaded = False

    def set_repository(self, repository) -> None:
        """Liga um store duravel. `None` volta ao modo apenas-memoria."""
        self._repository = repository
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Reidrata do store na primeira leitura apos um restart.

        Preguicoso de proposito: quem roda sem persistencia nao paga nada, e
        quem roda com ela paga uma vez.
        """
        if self._loaded or self._repository is None:
            return
        # Marcado ANTES de carregar: um erro aqui nao pode virar laco de
        # tentativa a cada chamada.
        self._loaded = True
        for entrada in self._repository.load_models():
            self._entries.setdefault(entrada.model_key, entrada)
        conhecidas = {
            (i.model_key, i.to_status, i.occurred_at) for i in self._history
        }
        for transicao in self._repository.load_transitions():
            chave = (transicao.model_key, transicao.to_status, transicao.occurred_at)
            if chave not in conhecidas:
                self._history.append(transicao)

    def _persist(self, entry: ModelEntry, transition: ModelTransition | None = None) -> None:
        if self._repository is None:
            return
        self._repository.save_model(entry)
        if transition is not None:
            self._repository.save_transition(transition)

    # --- registro ---------------------------------------------------------

    def register(
        self,
        *,
        provider: str,
        model_name: str,
        model_version: str,
        capabilities: tuple[ModelCapability, ...] = (),
        notes: str | None = None,
        now: datetime | None = None,
    ) -> ModelEntry:
        """Registra um modelo. Ele nasce REGISTERED, nunca em producao."""
        self._ensure_loaded()
        chave = self.model_key(provider, model_name, model_version)
        if chave in self._entries:
            raise ModelRegistryError(f"Modelo já registrado: {chave}")

        entrada = ModelEntry(
            model_key=chave,
            provider=provider.strip().lower(),
            model_name=model_name.strip(),
            model_version=model_version.strip(),
            capabilities=capabilities,
            created_at=now or datetime.now(timezone.utc),
            notes=notes,
        )
        self._entries[chave] = entrada
        self._persist(entrada)
        return entrada

    @staticmethod
    def model_key(provider: str, model_name: str, model_version: str) -> str:
        return f"{provider.strip().lower()}:{model_name.strip()}:{model_version.strip()}"

    def find(self, model_key: str) -> ModelEntry | None:
        self._ensure_loaded()
        return self._entries.get(model_key.strip())

    def list(self, status: ModelStatus | None = None) -> list[ModelEntry]:
        self._ensure_loaded()
        itens = sorted(self._entries.values(), key=lambda item: item.model_key)
        return [item for item in itens if status is None or item.status is status]

    def promoted(self) -> list[ModelEntry]:
        return self.list(ModelStatus.PROMOTED)

    def history(self, model_key: str) -> list[ModelTransition]:
        self._ensure_loaded()
        return [item for item in self._history if item.model_key == model_key]

    # --- ciclo de vida ----------------------------------------------------

    def transition(
        self,
        model_key: str,
        target: ModelStatus,
        *,
        reason: str,
        actor: str,
        evaluation_id: str | None = None,
        now: datetime | None = None,
    ) -> ModelEntry:
        """Move o modelo de estado, ou recusa dizendo exatamente por que.

        Tres recusas, e nenhuma delas negociavel:

        1. transicao fora da tabela declarada;
        2. estado que exige evidencia sem `evaluation_id`;
        3. modelo inexistente.
        """
        self._ensure_loaded()
        entrada = self._entries.get(model_key.strip())
        if entrada is None:
            raise ModelRegistryError(f"Modelo não registrado: {model_key}")

        if not transition_allowed(entrada.status, target):
            raise ModelRegistryError(
                f"Transição não permitida: {entrada.status.value} -> {target.value}. "
                "Não existe caminho direto para produção."
            )

        if requires_evidence(target) and not evaluation_id:
            raise ModelRegistryError(
                f"{target.value} exige evaluation_id: promoção sem evidência "
                "não é promoção."
            )

        instante = now or datetime.now(timezone.utc)
        avaliacoes = entrada.evaluation_ids
        if evaluation_id and evaluation_id not in avaliacoes:
            avaliacoes = avaliacoes + (evaluation_id,)

        atualizacao = {
            "status": target,
            "evaluation_ids": avaliacoes,
        }
        if target is ModelStatus.PROMOTED:
            atualizacao["promoted_at"] = instante
        elif target is ModelStatus.REJECTED:
            atualizacao["rejected_at"] = instante
        elif target is ModelStatus.ROLLED_BACK:
            atualizacao["rolled_back_at"] = instante

        anterior = entrada.status
        nova = entrada.model_copy(update=atualizacao)
        # Revalida: `model_copy` nao dispara validador, e um estado invalido
        # gravado aqui so apareceria muito depois.
        nova = ModelEntry.model_validate(nova.model_dump())
        self._entries[nova.model_key] = nova

        registro = ModelTransition(
                model_key=nova.model_key,
                from_status=anterior,
                to_status=target,
                reason=reason,
                evaluation_id=evaluation_id,
            actor=actor,
            occurred_at=instante,
        )
        self._history.append(registro)
        self._persist(nova, registro)
        return nova

    def rollback(
        self, model_key: str, *, reason: str, actor: str, now: datetime | None = None
    ) -> ModelEntry:
        """Volta um modelo promovido. Sempre disponivel, por escolha."""
        return self.transition(
            model_key,
            ModelStatus.ROLLED_BACK,
            reason=reason,
            actor=actor,
            now=now,
        )

    def reset(self) -> None:
        self._entries.clear()
        self._history.clear()
        self._loaded = False


model_registry_service = ModelRegistryService()
