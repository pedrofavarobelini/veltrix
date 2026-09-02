"""E3, E10 e E12 — Control Center, SLO e Disaster Recovery.

O foco: o painel nao muta nada nem vaza nada, a saude nao inventa numero que
nao mediu, e o backup e PROVADO restaurando sobre estado destruido.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.control_center.service import control_center_service
from app.modules.disaster_recovery.service import (
    CRITICAL_STORES,
    RestoreOutcome,
    StoreCriticality,
    digest_of,
    disaster_recovery_service,
    restore_sequence,
)
from app.modules.evaluation_plane.service import evaluation_plane_service
from app.modules.model_registry.service import model_registry_service
from app.modules.slo.service import (
    MIN_SAMPLE,
    HealthState,
    SLIKind,
    SLOService,
    slo_service,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
CORE_KEY = "platform-control-key-synthetic"


@pytest.fixture(autouse=True)
def limpa():
    slo_service.reset()
    model_registry_service.reset()
    evaluation_plane_service.reset()
    yield
    slo_service.reset()
    model_registry_service.reset()
    evaluation_plane_service.reset()


# ===========================================================================
# E10 — SLO / saude operacional
# ===========================================================================


def test_an_indicator_without_measurement_is_unknown_never_healthy():
    """Verde por falta de dado é pior que painel vazio."""
    leitura = SLOService().reading(SLIKind.AVAILABILITY)
    assert leitura.state is HealthState.UNKNOWN
    assert leitura.value is None
    assert leitura.reason_code == "INSUFFICIENT_SAMPLE"


def test_a_sample_below_the_minimum_stays_unknown():
    """Três sucessos não provam disponibilidade."""
    service = SLOService()
    for _ in range(MIN_SAMPLE - 1):
        service.observe(SLIKind.AVAILABILITY, 1.0)
    assert service.reading(SLIKind.AVAILABILITY).state is HealthState.UNKNOWN


def test_enough_good_samples_report_healthy():
    service = SLOService()
    for _ in range(MIN_SAMPLE):
        service.observe(SLIKind.AVAILABILITY, 1.0)
    leitura = service.reading(SLIKind.AVAILABILITY)
    assert leitura.state is HealthState.HEALTHY
    assert leitura.sample_size == MIN_SAMPLE


def test_two_thresholds_give_time_to_react():
    """Um sistema que só soubesse 'bom' e 'morto' não deixaria reagir."""
    service = SLOService()
    for _ in range(MIN_SAMPLE):
        service.observe(SLIKind.ERROR_RATE, 0.05)
    assert service.reading(SLIKind.ERROR_RATE).state is HealthState.DEGRADED

    outro = SLOService()
    for _ in range(MIN_SAMPLE):
        outro.observe(SLIKind.ERROR_RATE, 0.5)
    assert outro.reading(SLIKind.ERROR_RATE).state is HealthState.UNAVAILABLE


def test_an_indicator_where_lower_is_worse_is_read_in_the_right_direction():
    """Disponibilidade baixa é ruim; latência baixa é boa."""
    service = SLOService()
    for _ in range(MIN_SAMPLE):
        service.observe(SLIKind.AVAILABILITY, 0.5)
    assert service.reading(SLIKind.AVAILABILITY).state is HealthState.UNAVAILABLE

    outro = SLOService()
    for _ in range(MIN_SAMPLE):
        outro.observe(SLIKind.LATENCY, 0.1)
    assert outro.reading(SLIKind.LATENCY).state is HealthState.HEALTHY


def test_the_worst_indicator_decides_the_aggregate():
    service = SLOService()
    for _ in range(MIN_SAMPLE):
        service.observe(SLIKind.AVAILABILITY, 1.0)
        service.observe(SLIKind.ERROR_RATE, 0.5)
    assert service.snapshot().state is HealthState.UNAVAILABLE


def test_the_snapshot_lists_which_indicators_are_unknown():
    """Saber o que não se sabe é parte do relatório."""
    instantaneo = SLOService().snapshot()
    assert set(instantaneo.unknown) == {item.value for item in SLIKind}
    assert instantaneo.state is HealthState.UNKNOWN


def test_every_indicator_declares_its_targets():
    service = SLOService()
    for leitura in service.snapshot().readings:
        assert leitura.unit
        assert leitura.target_degraded_at is not None
        assert leitura.target_unavailable_at is not None


def test_the_series_is_bounded_so_cardinality_cannot_explode():
    service = SLOService(window=10)
    for valor in range(100):
        service.observe(SLIKind.LATENCY, float(valor))
    assert service.reading(SLIKind.LATENCY).sample_size == 10


# ===========================================================================
# E12 — Disaster Recovery
# ===========================================================================


def _snapshots() -> dict:
    """Estado sintetico. Nenhum dado real, nenhum dado de consumidor."""
    return {
        "caller_identity": [{"credential_id": "sintetico-a", "project_id": "alpha"}],
        "policy_assets": [{"asset_id": "assistant.system", "version": 1}],
        "postgresql": [{"table": "pedrocore_reports", "rows": 3}],
        "risk_history": [{"analysis_id": "analysis_sintetico", "severity": "LOW"}],
        "outbox": [{"entry_id": "outbox-1", "state": "pending"}],
    }


def test_the_declared_restore_order_is_internally_consistent():
    """Dependência que restaura depois é o pior modo de falha: não aparece."""
    sequencia = restore_sequence()
    posicao = {item.store_id: indice for indice, item in enumerate(sequencia)}
    for item in sequencia:
        for dependencia in item.depends_on:
            assert posicao[dependencia] < posicao[item.store_id]


def test_identity_restores_first_and_outbox_last():
    """Reentregar antes de o destino existir duplicaria efeito."""
    ordem = [item.store_id for item in restore_sequence()]
    assert ordem[0] == "caller_identity"
    assert ordem[-1] == "outbox"


def test_every_critical_store_is_mapped_with_a_criticality():
    assert CRITICAL_STORES
    for item in CRITICAL_STORES:
        assert isinstance(item.criticality, StoreCriticality)
        assert item.description


def test_a_faithful_restore_is_verified():
    manifesto = disaster_recovery_service.backup(
        _snapshots(), backup_id="drill-001", now=NOW
    )
    verificacao = disaster_recovery_service.verify_restore(
        manifesto, _snapshots(), now=NOW
    )
    assert verificacao.outcome is RestoreOutcome.VERIFIED
    assert verificacao.proven is True
    assert verificacao.mismatched_stores == []


def test_a_single_diverging_store_fails_the_whole_restore():
    """Restauração parcial silenciosa é sistema incompleto se dizendo completo."""
    manifesto = disaster_recovery_service.backup(
        _snapshots(), backup_id="drill-002", now=NOW
    )
    corrompido = _snapshots()
    corrompido["risk_history"] = [{"analysis_id": "outro", "severity": "CRITICAL"}]

    verificacao = disaster_recovery_service.verify_restore(manifesto, corrompido, now=NOW)
    assert verificacao.outcome is RestoreOutcome.INTEGRITY_FAILED
    assert verificacao.proven is False
    assert "risk_history" in verificacao.mismatched_stores


def test_a_missing_store_makes_the_restore_incomplete():
    manifesto = disaster_recovery_service.backup(
        _snapshots(), backup_id="drill-003", now=NOW
    )
    parcial = _snapshots()
    del parcial["outbox"]

    verificacao = disaster_recovery_service.verify_restore(manifesto, parcial, now=NOW)
    assert verificacao.outcome is RestoreOutcome.INCOMPLETE
    assert "outbox" in verificacao.missing_stores


def test_the_full_drill_destroys_before_restoring():
    """Sem destruir, o teste passaria mesmo com um backup vazio."""
    estado = _snapshots()
    destruido: list[bool] = []

    def destroy():
        estado.clear()
        destruido.append(True)

    def restore(manifest):
        assert estado == {}, "restauração começou antes de o estado ser destruído"
        return _snapshots()

    verificacao = disaster_recovery_service.run_drill(
        _snapshots(),
        destroy=destroy,
        restore=restore,
        backup_id="drill-004",
        now=NOW,
    )
    assert destruido == [True]
    assert verificacao.outcome is RestoreOutcome.VERIFIED


def test_an_empty_restore_after_destruction_does_not_pass():
    """A prova precisa poder reprovar."""
    verificacao = disaster_recovery_service.run_drill(
        _snapshots(),
        destroy=lambda: None,
        restore=lambda manifest: {},
        backup_id="drill-005",
        now=NOW,
    )
    assert verificacao.outcome is RestoreOutcome.INCOMPLETE


def test_a_failing_restore_is_reported_without_leaking_the_message():
    segredo = "postgresql://user:supersecret@host/db"

    def restore(manifest):
        raise ConnectionError(segredo)

    verificacao = disaster_recovery_service.run_drill(
        _snapshots(),
        destroy=lambda: None,
        restore=restore,
        backup_id="drill-006",
        now=NOW,
    )
    assert verificacao.outcome is RestoreOutcome.FAILED
    assert segredo not in json.dumps(verificacao.model_dump(mode="json"))
    assert "CONNECTIONERROR" in verificacao.reason_codes[0]


def test_the_manifest_declares_whether_it_holds_production_data():
    manifesto = disaster_recovery_service.backup(
        _snapshots(), backup_id="drill-007", now=NOW
    )
    assert manifesto.contains_production_data is False


def test_the_digest_detects_any_content_change():
    assert digest_of({"a": 1}) != digest_of({"a": 2})
    assert digest_of({"a": 1, "b": 2}) == digest_of({"b": 2, "a": 1})


# ===========================================================================
# E3 — Control Center
# ===========================================================================


def test_the_snapshot_aggregates_what_each_layer_already_knows():
    retrato = control_center_service.snapshot(now=NOW)
    assert retrato.projects, "nenhum projeto registrado no retrato"
    assert retrato.health_state in {item.value for item in HealthState}
    assert retrato.risk.persistence_mode
    assert retrato.resilience.outbox_mode


def test_the_snapshot_is_declared_read_only():
    retrato = control_center_service.snapshot(now=NOW)
    assert retrato.read_only is True
    assert retrato.contains_sensitive_data is False


def test_the_control_center_exposes_no_mutating_operation():
    """Painel que mutasse estado seria uma segunda porta para decisões."""
    proibidos = {"delete", "promote", "approve", "reprocess", "purge", "reset"}
    metodos = {
        nome
        for nome in dir(control_center_service)
        if not nome.startswith("_")
    }
    assert not (metodos & proibidos)


def test_the_signing_key_is_reported_as_presence_never_as_value(monkeypatch):
    """Um painel que mostrasse a chave seria um painel que vaza a chave."""
    chave = "synthetic-control-center-signing-key-com-mais-de-32"
    monkeypatch.setenv("PEDROCORE_RISK_CONTRACT_SIGNING_KEY", chave)
    retrato = control_center_service.snapshot(now=NOW)
    assert retrato.risk.contract_signing_configured is True
    assert chave not in json.dumps(retrato.model_dump(mode="json"))


def test_a_short_signing_key_is_not_reported_as_configured(monkeypatch):
    monkeypatch.setenv("PEDROCORE_RISK_CONTRACT_SIGNING_KEY", "curta")
    assert control_center_service.snapshot(now=NOW).risk.contract_signing_configured is False


def test_projects_are_reported_by_what_they_declare():
    retrato = control_center_service.snapshot(now=NOW)
    pedrocore = next(i for i in retrato.projects if i.project_id == "pedrocore")
    assert "risk_analysis" in pedrocore.capabilities


# --- rotas -----------------------------------------------------------------


def _registry() -> str:
    return json.dumps(
        [
            {
                "credential_id": "platform-technical-tool",
                "api_key": CORE_KEY,
                "project_id": "pedrocore",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["pedrocore"],
            }
        ]
    )


def test_the_platform_routes_require_authentication(monkeypatch):
    """Com registro configurado, chamada sem credencial nao passa.

    O registro precisa estar configurado: sem ele a API roda em modo
    dev/local e libera — comportamento que ja existia e nao e desta frente.
    """
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    for rota in ("/api/control-center/snapshot", "/api/health/slo"):
        assert client.get(rota).status_code == 401


def test_the_compatibility_route_requires_authentication(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    resposta = client.post(
        "/api/compatibility/check",
        json={"project_id": "pedrocore", "capability": "risk_analysis"},
    )
    assert resposta.status_code == 401


def test_an_invalid_credential_is_refused(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    resposta = client.get(
        "/api/control-center/snapshot", headers={AUTH_HEADER: "chave-forjada"}
    )
    assert resposta.status_code == 401


def test_an_authenticated_caller_reads_the_snapshot(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    resposta = client.get(
        "/api/control-center/snapshot", headers={AUTH_HEADER: CORE_KEY}
    )
    assert resposta.status_code == 200
    assert resposta.json()["read_only"] is True


def test_a_caller_cannot_ask_compatibility_for_another_project(monkeypatch):
    """Perguntar por outro projeto revelaria o que ele declara."""
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    resposta = client.post(
        "/api/compatibility/check",
        headers={AUTH_HEADER: CORE_KEY},
        json={"project_id": "structa", "capability": "risk_analysis"},
    )
    assert resposta.status_code == 403


def test_the_compatibility_route_answers_for_the_authenticated_project(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    resposta = client.post(
        "/api/compatibility/check",
        headers={AUTH_HEADER: CORE_KEY},
        json={"project_id": "pedrocore", "capability": "risk_analysis"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "SUPPORTED"


def test_the_slo_route_reports_unknown_without_measurements(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    resposta = client.get("/api/health/slo", headers={AUTH_HEADER: CORE_KEY})
    assert resposta.status_code == 200
    assert resposta.json()["state"] == "UNKNOWN"
