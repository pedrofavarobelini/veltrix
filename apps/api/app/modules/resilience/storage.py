"""Leitura segura de estado durável em arquivo.

O problema que este módulo corrige
-----------------------------------

A primeira versão do outbox durável tratava arquivo corrompido assim:

    try:
        raw = json.loads(self._file.read_text())
    except (OSError, json.JSONDecodeError):
        return          # <- store vazio

Isso é pior do que não persistir. Um arquivo ilegível vira "fila vazia", o
consumidor conclui que não há nada pendente, e a **próxima escrita sobrescreve
o arquivo** — apagando entregas que ninguém chegou a ver. A falha silenciosa
transforma corrupção recuperável em perda definitiva.

O mesmo valia por registro: um item que falhava ao validar era descartado com
`continue`. Uma entrega pendente sumia sem que nada reclamasse.

A regra correta
---------------

Estado durável ilegível é **corrupção**, e corrupção é um evento, não um
arquivo vazio:

  1. detectar — parse do arquivo E validação de cada registro;
  2. preservar — cópia em quarentena, com o original intocado;
  3. degradar — a camada de entrega recusa escrita até alguém olhar;
  4. nunca fingir vazio.

Preservar por CÓPIA e não por renomeação é deliberado: renomear libera o
caminho original, e a próxima escrita criaria um arquivo novo por cima — que é
exatamente o desaparecimento que se quer impedir.

O que não vaza
--------------

O erro carrega caminho, contagem e motivo. Nunca o conteúdo: um arquivo
corrompido de outbox contém payloads de evidência, e reproduzi-los na mensagem
os colocaria no log de quem estava tentando protegê-los.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DurableStorageCorruptionError(RuntimeError):
    """Estado durável ilegível. Carrega diagnóstico, nunca conteúdo."""

    def __init__(self, path: Path, reason: str, quarantine: Path | None = None) -> None:
        self.path = path
        self.reason = reason
        self.quarantine = quarantine
        detail = f"; cópia preservada em {quarantine.name}" if quarantine else ""
        super().__init__(
            f"Estado durável corrompido em {path.name}: {reason}{detail}. "
            "A camada de entrega está em modo degradado e não grava até revisão."
        )


class DurableStorageDegradedError(RuntimeError):
    """Escrita recusada porque o armazenamento está degradado.

    Existe separada da corrupção porque as duas perguntas são diferentes: uma é
    "o que eu li está quebrado?", a outra é "posso gravar agora?". Quem chama
    precisa poder distinguir para decidir se continua o fluxo principal.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Armazenamento durável {path.name} está degradado por corrupção "
            "detectada; escrita bloqueada para não sobrescrever evidência pendente."
        )


def quarantine_corrupted(path: Path) -> Path | None:
    """Copia o arquivo corrompido para um nome de quarentena.

    Cópia, e não movimentação: mover libera o caminho original e a próxima
    escrita criaria um arquivo novo por cima. O original fica onde está,
    ilegível mas presente, até alguém decidir o que fazer com ele.
    """
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        shutil.copy2(path, target)
    except OSError:
        # Não conseguir preservar não pode mascarar a corrupção: o chamador
        # ainda precisa saber que o arquivo está ilegível.
        return None
    return target


def load_json_records(path: Path) -> list[Any] | None:
    """Lê uma lista de registros, ou `None` se o arquivo não existe.

    Levanta `DurableStorageCorruptionError` quando o arquivo existe e não pode
    ser lido como lista JSON. Nunca devolve lista vazia para arquivo ilegível —
    é justamente essa confusão que o módulo existe para impedir.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise DurableStorageCorruptionError(
            path, f"arquivo ilegível ({type(error).__name__})", quarantine_corrupted(path)
        ) from error

    if not text.strip():
        # Arquivo vazio é ambíguo: pode ser store legitimamente sem itens, ou
        # truncamento. Tratado como vazio legítimo porque a escrita é atômica —
        # este processo nunca produz um arquivo pela metade.
        return []

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise DurableStorageCorruptionError(
            path, "conteúdo não é JSON válido", quarantine_corrupted(path)
        ) from error

    if not isinstance(raw, list):
        raise DurableStorageCorruptionError(
            path, f"esperava lista, encontrou {type(raw).__name__}", quarantine_corrupted(path)
        )
    return raw


def load_json_object(path: Path) -> dict | None:
    """Mesma garantia de `load_json_records`, para um objeto no topo."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise DurableStorageCorruptionError(
            path, f"arquivo ilegível ({type(error).__name__})", quarantine_corrupted(path)
        ) from error

    if not text.strip():
        return {}

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise DurableStorageCorruptionError(
            path, "conteúdo não é JSON válido", quarantine_corrupted(path)
        ) from error

    if not isinstance(raw, dict):
        raise DurableStorageCorruptionError(
            path, f"esperava objeto, encontrou {type(raw).__name__}", quarantine_corrupted(path)
        )
    return raw


def parse_records(path: Path, raw: list[Any], model: type) -> list[Any]:
    """Valida cada registro. Um item inválido é corrupção, não item a pular.

    Descartar silenciosamente o registro ruim faria uma entrega pendente sumir
    sem que nada reclamasse — o mesmo defeito do arquivo vazio, só que por
    linha.
    """
    parsed: list[Any] = []
    for index, item in enumerate(raw):
        try:
            parsed.append(model(**item))
        except Exception as error:
            raise DurableStorageCorruptionError(
                path,
                f"registro {index} inválido ({type(error).__name__})",
                quarantine_corrupted(path),
            ) from error
    return parsed
