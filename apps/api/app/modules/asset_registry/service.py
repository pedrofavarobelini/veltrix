"""Servico do Asset Registry: versionar, ativar, comparar e reverter.

Invariante central: no maximo UMA versao ativa por asset. Duas ativas
significariam que ninguem sabe qual rodou — e a pergunta que este registry
existe para responder e exatamente essa.
"""

from __future__ import annotations

import difflib
from datetime import datetime, timezone

from app.modules.asset_registry.schemas import (
    AssetKind,
    AssetRecord,
    AssetStatus,
    AssetVersion,
    content_hash,
    transition_allowed,
)


class AssetRegistryError(RuntimeError):
    """Recusa explicita do registry."""


class AssetRegistryService:
    """Registro versionado de assets governados."""

    def __init__(self) -> None:
        self._records: dict[str, AssetRecord] = {}
        self._repository = None
        self._loaded = False

    def set_repository(self, repository) -> None:
        """Liga um store duravel. `None` volta ao modo apenas-memoria."""
        self._repository = repository
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Reidrata as versoes do store na primeira leitura apos restart."""
        if self._loaded or self._repository is None:
            return
        self._loaded = True
        for versao in self._repository.load_asset_versions():
            registro = self._records.get(versao.asset_id)
            if registro is None:
                registro = AssetRecord(asset_id=versao.asset_id, kind=versao.kind)
                self._records[versao.asset_id] = registro
            if not any(i.version == versao.version for i in registro.versions):
                registro.versions.append(versao)
        for registro in self._records.values():
            registro.versions.sort(key=lambda item: item.version)

    def _persist(self, *versions: AssetVersion) -> None:
        if self._repository is None:
            return
        for versao in versions:
            self._repository.save_asset_version(versao)

    # --- escrita ----------------------------------------------------------

    def publish(
        self,
        *,
        asset_id: str,
        kind: AssetKind,
        content: str,
        provenance: str,
        author: str,
        change_reason: str,
        compatible_policy_version: str | None = None,
        compatible_contract_versions: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> AssetVersion:
        """Cria uma versao nova em DRAFT.

        Nasce em DRAFT e nao em ACTIVE de proposito: publicar e ativar sao
        decisoes diferentes, e juntar as duas faria toda escrita virar um
        deploy.
        """
        self._ensure_loaded()
        chave = asset_id.strip()
        registro = self._records.get(chave)
        if registro is None:
            registro = AssetRecord(asset_id=chave, kind=kind)
            self._records[chave] = registro
        elif registro.kind is not kind:
            raise AssetRegistryError(
                f"Asset {chave} já existe como {registro.kind.value}; "
                "mudar o tipo criaria dois assets com a mesma identidade."
            )

        anterior = registro.latest
        if anterior is not None and anterior.content_hash == content_hash(content):
            # Conteudo identico nao merece versao nova: a historia ficaria
            # cheia de linhas que nao mudaram nada, e a comparacao entre
            # versoes perderia o sentido.
            raise AssetRegistryError(
                f"Conteúdo idêntico à versão {anterior.version}; "
                "nada mudou e nenhuma versão foi criada."
            )

        versao = AssetVersion(
            asset_id=chave,
            version=(anterior.version + 1) if anterior else 1,
            kind=kind,
            status=AssetStatus.DRAFT,
            content=content,
            content_hash=content_hash(content),
            provenance=provenance,
            author=author,
            change_reason=change_reason,
            created_at=now or datetime.now(timezone.utc),
            compatible_policy_version=compatible_policy_version,
            compatible_contract_versions=compatible_contract_versions,
        )
        registro.versions.append(versao)
        self._persist(versao)
        return versao

    def activate(self, asset_id: str, version: int) -> AssetVersion:
        """Ativa uma versao e aposenta a anterior, em um passo so.

        Duas ativas ao mesmo tempo seria pior do que nenhuma: ninguem saberia
        qual rodou, e o registry passaria a mentir sobre a propria pergunta.
        """
        registro, alvo = self._locate(asset_id, version)
        if not transition_allowed(alvo.status, AssetStatus.ACTIVE):
            raise AssetRegistryError(
                f"Transição não permitida: {alvo.status.value} -> ACTIVE"
            )

        novas: list[AssetVersion] = []
        for item in registro.versions:
            if item.version == version:
                novas.append(item.model_copy(update={"status": AssetStatus.ACTIVE}))
            elif item.status is AssetStatus.ACTIVE:
                novas.append(item.model_copy(update={"status": AssetStatus.DEPRECATED}))
            else:
                novas.append(item)
        registro.versions = novas
        self._persist(*novas)
        return self._version(registro, version)

    def rollback(self, asset_id: str, to_version: int) -> AssetVersion:
        """Volta para uma versao anterior, marcando a atual como revertida."""
        registro, alvo = self._locate(asset_id, to_version)
        novas: list[AssetVersion] = []
        for item in registro.versions:
            if item.version == to_version:
                novas.append(item.model_copy(update={"status": AssetStatus.ACTIVE}))
            elif item.status is AssetStatus.ACTIVE:
                novas.append(
                    item.model_copy(update={"status": AssetStatus.ROLLED_BACK})
                )
            else:
                novas.append(item)
        registro.versions = novas
        self._persist(*novas)
        return self._version(registro, to_version)

    def deprecate(self, asset_id: str, version: int) -> AssetVersion:
        registro, alvo = self._locate(asset_id, version)
        if not transition_allowed(alvo.status, AssetStatus.DEPRECATED):
            raise AssetRegistryError(
                f"Transição não permitida: {alvo.status.value} -> DEPRECATED"
            )
        registro.versions = [
            item.model_copy(update={"status": AssetStatus.DEPRECATED})
            if item.version == version
            else item
            for item in registro.versions
        ]
        self._persist(*registro.versions)
        return self._version(registro, version)

    # --- leitura ----------------------------------------------------------

    def record(self, asset_id: str) -> AssetRecord | None:
        self._ensure_loaded()
        return self._records.get(asset_id.strip())

    def active_for(self, asset_id: str) -> AssetVersion | None:
        registro = self.record(asset_id)
        return registro.active if registro else None

    def list_assets(self, kind: AssetKind | None = None) -> list[AssetRecord]:
        self._ensure_loaded()
        itens = sorted(self._records.values(), key=lambda item: item.asset_id)
        return [item for item in itens if kind is None or item.kind is kind]

    def diff(self, asset_id: str, left: int, right: int) -> str:
        """Comparacao textual entre duas versoes, para revisao humana."""
        _, a = self._locate(asset_id, left)
        _, b = self._locate(asset_id, right)
        linhas = difflib.unified_diff(
            a.content.splitlines(),
            b.content.splitlines(),
            fromfile=f"{asset_id}@{left}",
            tofile=f"{asset_id}@{right}",
            lineterm="",
        )
        return "\n".join(linhas)

    def reset(self) -> None:
        self._records.clear()
        self._loaded = False

    # --- apoio ------------------------------------------------------------

    def _locate(self, asset_id: str, version: int) -> tuple[AssetRecord, AssetVersion]:
        self._ensure_loaded()
        registro = self._records.get(asset_id.strip())
        if registro is None:
            raise AssetRegistryError(f"Asset não registrado: {asset_id}")
        for item in registro.versions:
            if item.version == version:
                return registro, item
        raise AssetRegistryError(f"Versão {version} não existe em {asset_id}")

    @staticmethod
    def _version(record: AssetRecord, version: int) -> AssetVersion:
        for item in record.versions:
            if item.version == version:
                return item
        raise AssetRegistryError(f"Versão {version} desapareceu de {record.asset_id}")


asset_registry_service = AssetRegistryService()
