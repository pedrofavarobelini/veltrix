"""Validação estrutural das migrations, sem precisar de banco.

Por que offline
---------------

Os testes de migration existentes exigem `PEDROCORE_TEST_POSTGRES_URL` e ficam
skipped na maior parte dos ambientes — inclusive no meu. Isso significa que uma
migration quebrada só apareceria no primeiro ambiente que tivesse banco, que
provavelmente é produção.

Esta suíte não substitui aqueles testes. Ela pega, sem banco nenhum, a classe
de erro que é barata de pegar cedo e cara de descobrir tarde: arquivo fora de
ordem, migration destrutiva, tabela sem chave primária, `CREATE` sem
`IF NOT EXISTS`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"

# Comandos que apagam ou reescrevem estrutura existente. O runner aplica cada
# arquivo uma única vez e guarda checksum, mas um arquivo destrutivo aplicado
# uma vez já basta para perder dado.
_DESTRUCTIVE = re.compile(
    r"\b(DROP\s+TABLE|DROP\s+COLUMN|DROP\s+DATABASE|TRUNCATE|DELETE\s+FROM)\b",
    re.IGNORECASE,
)


def _files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def test_migrations_exist_and_are_numbered_in_sequence():
    """Numeração com buraco significa migration perdida no merge."""
    files = _files()
    assert files, "nenhuma migration encontrada"
    numbers = [int(file.name.split("_", 1)[0]) for file in files]
    assert numbers == list(range(1, len(files) + 1)), (
        f"numeração fora de sequência: {numbers}"
    )


def test_migration_filenames_are_ordered_lexicographically():
    """O runner aplica por `sorted(glob)`.

    Se a ordem lexicográfica divergir da numérica, as migrations rodam fora de
    ordem — e uma foreign key para uma tabela ainda inexistente falha.
    """
    files = [file.name for file in _files()]
    assert files == sorted(files)


@pytest.mark.parametrize("migration", _files(), ids=lambda item: item.name)
def test_migration_is_additive_only(migration: Path):
    """Migrations do PedroCore são aditivas. Remoção exige migration path."""
    content = migration.read_text(encoding="utf-8")
    # Comentários explicam o porquê e podem citar as palavras; só o SQL conta.
    sql = "\n".join(
        line for line in content.splitlines() if not line.strip().startswith("--")
    )
    found = _DESTRUCTIVE.findall(sql)
    assert not found, f"{migration.name} contém comando destrutivo: {found}"


@pytest.mark.parametrize("migration", _files(), ids=lambda item: item.name)
def test_migration_is_idempotent(migration: Path):
    """Reaplicar não pode falhar: o runner é chamado por gente, mais de uma vez."""
    sql = migration.read_text(encoding="utf-8")
    for statement, guard in (("CREATE TABLE", "IF NOT EXISTS"), ("CREATE INDEX", "IF NOT EXISTS")):
        for line in sql.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith(statement) and guard not in stripped.upper():
                pytest.fail(f"{migration.name}: '{stripped[:60]}' sem {guard}")


@pytest.mark.parametrize("migration", _files(), ids=lambda item: item.name)
def test_every_created_table_declares_a_primary_key(migration: Path):
    """Isolamento e unicidade dependem de chave, não de disciplina da aplicação."""
    sql = migration.read_text(encoding="utf-8")
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", sql, re.IGNORECASE)
    if not tables:
        return
    assert "PRIMARY KEY" in sql.upper(), (
        f"{migration.name} cria {tables} sem declarar PRIMARY KEY"
    )


def test_hardening_tables_are_present():
    """As tabelas de durabilidade existem como migration, não só como código."""
    combined = "\n".join(file.read_text(encoding="utf-8") for file in _files())
    for table in (
        "pedrocore_evidence_records",
        "pedrocore_outbox_entries",
        "pedrocore_dataset_definitions",
        "pedrocore_dataset_versions",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in combined, table


def test_no_migration_carries_a_literal_secret():
    """Migration é versionada para sempre; segredo aqui não sai mais."""
    pattern = re.compile(
        r"(password|secret|api[_-]?key|token)\s*=\s*'[^']{8,}'", re.IGNORECASE
    )
    for file in _files():
        assert not pattern.search(file.read_text(encoding="utf-8")), file.name
