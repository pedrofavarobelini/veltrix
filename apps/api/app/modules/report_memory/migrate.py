"""Runner explícito das migrações aditivas de Operational Persistence."""

import os
from pathlib import Path

from app.modules.report_memory.repository import apply_postgresql_migrations
from app.modules.report_memory.service import FLAG_DATABASE_URL


def main() -> int:
    database_url = (os.environ.get(FLAG_DATABASE_URL) or "").strip()
    if not database_url:
        raise SystemExit(f"{FLAG_DATABASE_URL} não configurada; migração não executada.")
    migration_dir = Path(__file__).resolve().parents[3] / "migrations"
    applied = apply_postgresql_migrations(database_url, migration_dir)
    print(f"Migrações aplicadas: {len(applied)}")
    for version in applied:
        print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
