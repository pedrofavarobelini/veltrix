"""Reconstrução de schema PostgreSQL durante uma recuperação.

O problema que este módulo existe para resolver
-----------------------------------------------

Foi encontrado rodando o ensaio de verdade, e não teria aparecido em nenhuma
comparação de estruturas em memória.

O runner de migrations é idempotente: ele mantém um livro-razão
(`pedrocore_schema_migrations`) e pula toda migração já registrada. Isso é
exatamente o comportamento certo no dia a dia — e é exatamente o comportamento
errado depois de um desastre.

Se as tabelas somem mas o livro-razão sobrevive, rodar o runner novamente NÃO
recria nada: ele lê que a `0011` já foi aplicada e segue adiante. O operador vê
"migrações aplicadas: 0", conclui que está tudo certo, e o banco continua sem
as tabelas.

Falha silenciosa, no pior momento possível.

A correção
----------

Reconstruir schema é declarar quais migrações precisam valer de novo. Este
módulo apaga as linhas correspondentes do livro-razão e reexecuta o runner —
nesta ordem, e sem tocar nas migrações que continuam válidas.

Por que não simplesmente apagar o livro-razão inteiro
-----------------------------------------------------

Porque isso reexecutaria migrações cujas tabelas nunca foram perdidas. Uma
migração aditiva costuma tolerar reexecução, mas "costuma" não é garantia, e
recuperação não é hora de descobrir a exceção.
"""

from __future__ import annotations

from pathlib import Path

import psycopg

MIGRATION_LEDGER = "pedrocore_schema_migrations"


class SchemaRebuildError(RuntimeError):
    """Falha ao reconstruir schema. Nunca silenciosa."""


def forget_migrations(database_url: str, versions: list[str]) -> list[str]:
    """Esquece migrações no livro-razão para que possam valer de novo.

    Devolve o que foi de fato esquecido — e não o que foi pedido. A diferença
    importa: pedir para esquecer uma migração que não estava registrada é sinal
    de que o operador e o banco discordam sobre o que aconteceu.
    """
    if not versions:
        return []
    try:
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            existe = connection.execute(
                "SELECT to_regclass(%s) IS NOT NULL", (MIGRATION_LEDGER,)
            ).fetchone()
            if not existe or not existe[0]:
                # Sem livro-razão não há o que esquecer: o runner vai aplicar
                # tudo do zero, que é o comportamento desejado.
                return []
            linhas = connection.execute(
                f"DELETE FROM {MIGRATION_LEDGER} WHERE version = ANY(%s) "  # noqa: S608
                "RETURNING version",
                (versions,),
            ).fetchall()
        return sorted(item[0] for item in linhas)
    except psycopg.Error as error:
        raise SchemaRebuildError(
            "Não foi possível ajustar o livro-razão de migrações durante a "
            "recuperação; o schema não foi reconstruído."
        ) from error


def rebuild_schema(
    database_url: str, migrations_dir: str | Path, versions: list[str]
) -> list[str]:
    """Reconstrói o schema das migrações indicadas.

    Passo obrigatório de qualquer restauração em que tabelas foram perdidas
    mas o banco continuou de pé. Sem ele, o runner não recria nada e a
    recuperação termina parecendo bem-sucedida.
    """
    forget_migrations(database_url, versions)

    from app.modules.report_memory.repository import apply_postgresql_migrations

    aplicadas = apply_postgresql_migrations(database_url, migrations_dir)

    faltando = [item for item in versions if item not in aplicadas]
    if faltando:
        raise SchemaRebuildError(
            "Migrações pedidas não foram reaplicadas: "
            + ", ".join(faltando)
            + ". O schema pode estar incompleto — a recuperação NÃO está provada."
        )
    return aplicadas


def tables_present(database_url: str, tables: list[str]) -> list[str]:
    """Quais das tabelas indicadas existem agora.

    Usado para verificar a reconstrução ANTES de reinserir dado: reinserir em
    tabela ausente falharia linha a linha, e o erro apontaria para o dado
    quando o problema é o schema.
    """
    try:
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            linhas = connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = ANY(%s)",
                (tables,),
            ).fetchall()
        return sorted(item[0] for item in linhas)
    except psycopg.Error as error:
        raise SchemaRebuildError(
            "Não foi possível verificar o schema durante a recuperação."
        ) from error
