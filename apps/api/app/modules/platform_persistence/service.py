"""Wiring da durabilidade das registries de plataforma.

Um lugar so decide se as tres registries persistem, e qual store usam. Deixar
cada servico ler a propria configuracao faria tres respostas possiveis para a
mesma pergunta — e um dia elas divergiriam.
"""

from __future__ import annotations

from app.modules.asset_registry.service import asset_registry_service
from app.modules.evaluation_plane.service import evaluation_plane_service
from app.modules.model_registry.service import model_registry_service
from app.modules.platform_persistence.repository import (
    PlatformRepository,
    build_platform_repository,
    platform_persistence_is_durable,
    platform_persistence_mode,
)


class PlatformPersistenceService:
    """Conecta e desconecta as tres registries do store configurado."""

    def __init__(self) -> None:
        self._repository: PlatformRepository | None = None
        self._wired = False

    def repository(self) -> PlatformRepository | None:
        """Store corrente, construido sob demanda a partir da configuracao.

        Em cache porque `build_platform_repository` le ambiente e valida: sem
        cache, cada acesso reconstruiria o store e a conexao.
        """
        if not self._wired:
            self._repository = build_platform_repository()
            self._wired = True
            self._attach()
        return self._repository

    def enabled(self) -> bool:
        return self.repository() is not None

    def durable(self) -> bool:
        """Sobrevive a restart? `memory` esta ligado e nao e duravel."""
        return self.enabled() and platform_persistence_is_durable()

    def mode(self) -> str:
        return platform_persistence_mode()

    def _attach(self) -> None:
        for servico in (
            model_registry_service,
            asset_registry_service,
            evaluation_plane_service,
        ):
            servico.set_repository(self._repository)

    def reset(self) -> None:
        """Solta o store e devolve as registries ao modo apenas-memoria.

        Usado por teste e por troca de configuracao. Nao apaga dado: quem
        apaga e `clear()` do proprio store.
        """
        self._repository = None
        self._wired = False
        for servico in (
            model_registry_service,
            asset_registry_service,
            evaluation_plane_service,
        ):
            servico.set_repository(None)


platform_persistence_service = PlatformPersistenceService()
