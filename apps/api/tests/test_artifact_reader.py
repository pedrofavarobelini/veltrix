import json

from fastapi.testclient import TestClient

from app.main import app
from app.modules.artifact_reader.service import artifact_reader_service

client = TestClient(app)

ENV_ENABLED = "PEDROCORE_ARTIFACT_READER_ENABLED"
ENV_DIRS = "PEDROCORE_ARTIFACT_ALLOWED_DIRS"
ENV_MAX_FILE = "PEDROCORE_ARTIFACT_MAX_FILE_CHARS"


def enable_reader(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_ENABLED, "true")
    monkeypatch.setenv(ENV_DIRS, str(tmp_path))


def test_reader_disabled_blocks(monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_ENABLED, raising=False)
    target = tmp_path / "a.txt"
    target.write_text("125 passed", encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_DISABLED" in result.warning_codes
    assert result.content is None


def test_reader_reads_allowlisted_file(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    target = tmp_path / "relatorio.txt"
    target.write_text("125 passed, 0 failed.", encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is True
    assert result.content == "125 passed, 0 failed."
    assert "ARTIFACT_READER_USED" in result.warning_codes
    # Garantia de que o arquivo não foi alterado nem removido.
    assert target.read_text(encoding="utf-8") == "125 passed, 0 failed."


def test_reader_blocks_outside_allowlist(monkeypatch, tmp_path):
    allowed = tmp_path / "permitido"
    outside = tmp_path / "fora"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setenv(ENV_ENABLED, "true")
    monkeypatch.setenv(ENV_DIRS, str(allowed))
    target = outside / "x.txt"
    target.write_text("conteudo", encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_PATH_NOT_ALLOWED" in result.warning_codes


def test_reader_blocks_path_traversal(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)

    result = artifact_reader_service.read(str(tmp_path / ".." / "escape.txt"))

    assert result.allowed is False
    assert "ARTIFACT_READER_PATH_TRAVERSAL_BLOCKED" in result.warning_codes


def test_reader_blocks_env_file(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    target = tmp_path / ".env"
    target.write_text("GEMINI_API_KEY=fake", encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_ENV_BLOCKED" in result.warning_codes
    assert result.content is None


def test_reader_blocks_disallowed_extension(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    target = tmp_path / "script.py"
    target.write_text("print('x')", encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_EXTENSION_BLOCKED" in result.warning_codes


def test_reader_blocks_large_file(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    monkeypatch.setenv(ENV_MAX_FILE, "100")
    target = tmp_path / "grande.log"
    target.write_text("x" * 500, encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_FILE_TOO_LARGE" in result.warning_codes


def test_reader_blocks_binary(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    target = tmp_path / "binario.log"
    target.write_bytes(b"abc\x00def")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_BINARY_BLOCKED" in result.warning_codes


def test_reader_blocks_identifiable_secret(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    target = tmp_path / "config.txt"
    target.write_text("password=SuperSecreta123!", encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_SECRET_BLOCKED" in result.warning_codes
    assert result.content is None


def test_reader_blocks_finguard_paths(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    finguard_dir = tmp_path / "finguard"
    finguard_dir.mkdir()
    target = finguard_dir / "relatorio.txt"
    target.write_text("125 passed", encoding="utf-8")

    result = artifact_reader_service.read(str(target))

    assert result.allowed is False
    assert "ARTIFACT_READER_PATH_NOT_ALLOWED" in result.warning_codes


def test_reader_never_writes_or_deletes(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    target = tmp_path / "dados.md"
    original = "# Relatório\n125 passed."
    target.write_text(original, encoding="utf-8")
    before = sorted(p.name for p in tmp_path.iterdir())

    artifact_reader_service.read(str(target))

    after = sorted(p.name for p in tmp_path.iterdir())
    assert before == after
    assert target.read_text(encoding="utf-8") == original


def test_orchestrate_with_reader_disabled_keeps_rejection(monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_ENABLED, raising=False)
    target = tmp_path / "r.txt"
    target.write_text("SEGREDO-LOCAL-NUNCA-LIDO", encoding="utf-8")

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "artifacts": [
                {"type": "text", "name": "r.txt", "metadata": {"path": str(target)}}
            ],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert "ARTIFACT_READER_DISABLED" in data["warning_codes"]
    assert "ARTIFACT_PATH_REJECTED" in data["warning_codes"]
    assert "SEGREDO-LOCAL-NUNCA-LIDO" not in json.dumps(data, ensure_ascii=False)


def test_orchestrate_with_reader_enabled_converts_file_to_artifact(monkeypatch, tmp_path):
    enable_reader(monkeypatch, tmp_path)
    target = tmp_path / "relatorio-qa.txt"
    target.write_text("All tests passed. 0 failed. Build successful.", encoding="utf-8")

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise o relatório lido do disco",
            "provider": "local_qa",
            "task_type": "qa_report_analysis",
            "artifacts": [
                {
                    "type": "text",
                    "name": "relatorio-qa.txt",
                    "metadata": {"path": str(target)},
                }
            ],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert "ARTIFACT_READER_USED" in data["warning_codes"]
    assert "ARTIFACT_PATH_REJECTED" not in data["warning_codes"]
    assert data["qa"] is not None
    assert data["qa"]["status"] == "pass"
    audit_dump = json.dumps(data["audit"], ensure_ascii=False)
    assert "All tests passed" not in audit_dump
