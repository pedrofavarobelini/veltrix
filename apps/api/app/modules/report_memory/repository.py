import json
from pathlib import Path

from app.modules.report_memory.schemas import ReportMemoryEntry

# Repositórios de memória técnica (PEDROCORE-REPORT-MEMORY-01).
#
# Padrão seguro: in-memory (in-process, volátil). Persistência local_json é
# opcional, default OFF, grava somente no diretório configurado pelo operador
# (testes usam tmp_path), nunca em .env e nunca dados com segredos (a
# sanitização acontece no serviço, antes de chegar aqui).

MAX_ENTRIES_PER_PROJECT = 50


class InMemoryReportMemoryRepository:
    def __init__(self) -> None:
        self._entries: dict[str, list[ReportMemoryEntry]] = {}

    def add(self, entry: ReportMemoryEntry) -> None:
        entries = self._entries.setdefault(entry.project_id, [])
        entries.append(entry)
        if len(entries) > MAX_ENTRIES_PER_PROJECT:
            del entries[: len(entries) - MAX_ENTRIES_PER_PROJECT]

    def list(self, project_id: str, limit: int | None = None) -> list[ReportMemoryEntry]:
        entries = list(self._entries.get(project_id, []))
        if limit is not None:
            return entries[-limit:]
        return entries

    def clear(self) -> None:
        self._entries.clear()


class LocalJsonReportMemoryRepository(InMemoryReportMemoryRepository):
    """Persistência local opcional: um arquivo JSON por projeto.

    Grava apenas dentro do diretório configurado (criado se necessário).
    Dados gerados em runtime não devem ser commitados.
    """

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _file_for(self, project_id: str) -> Path:
        safe_name = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in project_id
        )
        return self._directory / f"{safe_name}.json"

    def _load_all(self) -> None:
        for file in self._directory.glob("*.json"):
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for item in raw if isinstance(raw, list) else []:
                try:
                    entry = ReportMemoryEntry(**item)
                except Exception:
                    continue
                super().add(entry)

    def add(self, entry: ReportMemoryEntry) -> None:
        super().add(entry)
        entries = self.list(entry.project_id)
        payload = [item.model_dump() for item in entries]
        self._file_for(entry.project_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
