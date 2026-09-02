"""E1, E5, E8 e E11 — SDK, Model Registry, Asset Registry e Compatibilidade.

Reunidos num arquivo porque se provam juntos: a matriz responde perguntando
aos registries, e o SDK e o que faz a pergunta.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.asset_registry.schemas import (
    AssetKind,
    AssetStatus,
    AssetVersion,
    content_hash,
)
from app.modules.asset_registry.service import AssetRegistryError, asset_registry_service
from app.modules.compatibility.schemas import (
    CompatibilityQuery,
    CompatibilityStatus,
    worst,
)
from app.modules.compatibility.service import compatibility_service
from app.modules.consumer_sdk.client import (
    PedroCoreClient,
    PedroCoreConfig,
    PedroCoreConfigError,
    PedroCoreError,
    Response,
    idempotency_key,
)
from app.modules.consumer_sdk.version import SDK_VERSION
from app.modules.model_registry.schemas import ModelCapability, ModelStatus
from app.modules.model_registry.service import (
    ModelRegistryError,
    model_registry_service,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def limpa():
    model_registry_service.reset()
    asset_registry_service.reset()
    yield
    model_registry_service.reset()
    asset_registry_service.reset()


# ===========================================================================
# E5 — Model Registry
# ===========================================================================


def _register(**kw):
    return model_registry_service.register(
        provider=kw.pop("provider", "anthropic"),
        model_name=kw.pop("model_name", "claude-sonnet"),
        model_version=kw.pop("model_version", "5"),
        capabilities=(ModelCapability.TEXT,),
        now=NOW,
        **kw,
    )


def test_a_model_is_born_registered_never_in_production():
    entrada = _register()
    assert entrada.status is ModelStatus.REGISTERED
    assert entrada.usable_in_production is False


def test_there_is_no_direct_path_from_registered_to_promoted():
    """O atalho para produção é exatamente o que o registry existe para fechar."""
    entrada = _register()
    with pytest.raises(ModelRegistryError) as erro:
        model_registry_service.transition(
            entrada.model_key,
            ModelStatus.PROMOTED,
            reason="quero em produção",
            actor="alguem",
            evaluation_id="eval-1",
        )
    assert "não existe caminho direto" in str(erro.value).lower()


def test_promotion_without_evidence_is_refused():
    entrada = _register()
    for alvo in (ModelStatus.CANDIDATE, ModelStatus.EVALUATING):
        model_registry_service.transition(
            entrada.model_key, alvo, reason="avanço", actor="ci"
        )
    with pytest.raises(ModelRegistryError) as erro:
        model_registry_service.transition(
            entrada.model_key, ModelStatus.APPROVED, reason="aprovado", actor="ci"
        )
    assert "evidência" in str(erro.value)


def test_the_full_promotion_path_requires_evidence_and_records_it():
    entrada = _register()
    for alvo in (ModelStatus.CANDIDATE, ModelStatus.EVALUATING):
        model_registry_service.transition(
            entrada.model_key, alvo, reason="avanço", actor="ci"
        )
    aprovado = model_registry_service.transition(
        entrada.model_key,
        ModelStatus.APPROVED,
        reason="métricas dentro do limite",
        actor="revisor",
        evaluation_id="eval-abc",
    )
    assert "eval-abc" in aprovado.evaluation_ids

    promovido = model_registry_service.transition(
        entrada.model_key,
        ModelStatus.PROMOTED,
        reason="liberado para produção",
        actor="revisor",
        evaluation_id="eval-abc",
        now=NOW,
    )
    assert promovido.usable_in_production is True
    assert promovido.promoted_at == NOW


def test_a_promoted_model_can_always_be_rolled_back():
    """Toda promoção precisa ter volta."""
    entrada = _register()
    for alvo, ev in (
        (ModelStatus.CANDIDATE, None),
        (ModelStatus.EVALUATING, None),
        (ModelStatus.APPROVED, "eval-1"),
        (ModelStatus.PROMOTED, "eval-1"),
    ):
        model_registry_service.transition(
            entrada.model_key, alvo, reason="passo", actor="ci", evaluation_id=ev
        )
    revertido = model_registry_service.rollback(
        entrada.model_key, reason="regressão em produção", actor="oncall"
    )
    assert revertido.status is ModelStatus.ROLLED_BACK
    assert revertido.usable_in_production is False


def test_the_transition_history_is_auditable():
    entrada = _register()
    model_registry_service.transition(
        entrada.model_key, ModelStatus.CANDIDATE, reason="entrou na fila", actor="ci"
    )
    historia = model_registry_service.history(entrada.model_key)
    assert len(historia) == 1
    assert historia[0].from_status is ModelStatus.REGISTERED
    assert historia[0].reason == "entrou na fila"


def test_registering_the_same_model_twice_is_refused():
    _register()
    with pytest.raises(ModelRegistryError):
        _register()


def test_a_deprecated_model_is_terminal():
    entrada = _register()
    model_registry_service.transition(
        entrada.model_key, ModelStatus.DEPRECATED, reason="fim", actor="ci"
    )
    with pytest.raises(ModelRegistryError):
        model_registry_service.transition(
            entrada.model_key, ModelStatus.CANDIDATE, reason="voltar", actor="ci"
        )


# ===========================================================================
# E8 — Asset Registry
# ===========================================================================


def _publish(content="Você é um assistente técnico.", **kw):
    return asset_registry_service.publish(
        asset_id=kw.pop("asset_id", "assistant.system"),
        kind=kw.pop("kind", AssetKind.SYSTEM_PROMPT),
        content=content,
        provenance=kw.pop("provenance", "pedrocore/core"),
        author=kw.pop("author", "pedrocore-ci"),
        change_reason=kw.pop("change_reason", "versão inicial"),
        now=NOW,
        **kw,
    )


def test_an_asset_is_born_as_draft_not_active():
    """Publicar e ativar são decisões diferentes."""
    versao = _publish()
    assert versao.status is AssetStatus.DRAFT
    assert asset_registry_service.active_for("assistant.system") is None


def test_activating_a_version_retires_the_previous_one():
    """Duas versões ativas seria pior que nenhuma."""
    _publish()
    asset_registry_service.activate("assistant.system", 1)
    _publish(content="Você é um assistente técnico e conciso.")
    asset_registry_service.activate("assistant.system", 2)

    registro = asset_registry_service.record("assistant.system")
    ativas = [i for i in registro.versions if i.status is AssetStatus.ACTIVE]
    assert len(ativas) == 1
    assert ativas[0].version == 2


def test_rollback_restores_a_previous_version():
    _publish()
    asset_registry_service.activate("assistant.system", 1)
    _publish(content="Versão que deu errado.")
    asset_registry_service.activate("assistant.system", 2)

    voltou = asset_registry_service.rollback("assistant.system", 1)
    assert voltou.version == 1
    assert asset_registry_service.active_for("assistant.system").version == 1


def test_identical_content_does_not_create_a_new_version():
    """História cheia de linhas que não mudaram nada é história inútil."""
    _publish()
    with pytest.raises(AssetRegistryError) as erro:
        _publish()
    assert "idêntico" in str(erro.value)


@pytest.mark.parametrize(
    "conteudo",
    [
        "use api_key=ABCDEFGHIJKLMNOPQRSTUV",
        "conecte em postgres://user:senha123@host:5432/db",
        "token sk-abcdefghijklmnopqrstuvwx",
        "Authorization: Bearer abcdefghijklmnopqrstuv",
    ],
)
def test_a_secret_never_enters_the_registry(conteudo):
    """Um registry guarda para sempre: a recusa é na entrada."""
    with pytest.raises(Exception) as erro:
        _publish(content=conteudo)
    assert "segredo" in str(erro.value).lower() or "credencial" in str(erro.value).lower()


def test_the_hash_must_match_the_content():
    """Hash que não confere transformaria rastreabilidade em decoração."""
    with pytest.raises(Exception):
        AssetVersion(
            asset_id="a.b",
            version=1,
            kind=AssetKind.SYSTEM_PROMPT,
            content="conteúdo real",
            content_hash=content_hash("outro conteúdo"),
            provenance="p",
            author="a",
            change_reason="motivo",
            created_at=NOW,
        )


def test_two_versions_can_be_compared_for_human_review():
    _publish(content="linha um\nlinha dois")
    _publish(content="linha um\nlinha tres")
    diferenca = asset_registry_service.diff("assistant.system", 1, 2)
    assert "linha dois" in diferenca and "linha tres" in diferenca


def test_changing_the_kind_of_an_existing_asset_is_refused():
    _publish()
    with pytest.raises(AssetRegistryError):
        _publish(content="outro", kind=AssetKind.ROUTING_CONFIG)


# ===========================================================================
# E11 — Compatibility Matrix
# ===========================================================================


def test_the_worst_finding_decides_the_answer():
    assert (
        worst([CompatibilityStatus.SUPPORTED, CompatibilityStatus.INCOMPATIBLE])
        is CompatibilityStatus.INCOMPATIBLE
    )
    assert (
        worst([CompatibilityStatus.SUPPORTED, CompatibilityStatus.DEPRECATED])
        is CompatibilityStatus.DEPRECATED
    )


def test_unknown_is_worse_than_deprecated_but_not_incompatible():
    """Não saber é diferente de ser incompatível, e exige ação diferente."""
    assert (
        worst([CompatibilityStatus.DEPRECATED, CompatibilityStatus.UNKNOWN])
        is CompatibilityStatus.UNKNOWN
    )
    assert (
        worst([CompatibilityStatus.UNKNOWN, CompatibilityStatus.INCOMPATIBLE])
        is CompatibilityStatus.INCOMPATIBLE
    )


def test_a_registered_project_with_its_declared_capability_is_supported():
    resposta = compatibility_service.check(
        CompatibilityQuery(
            project_id="pedrocore",
            capability="risk_analysis",
            sdk_version=SDK_VERSION,
        )
    )
    assert resposta.status is CompatibilityStatus.SUPPORTED
    assert resposta.usable is True


def test_an_unregistered_project_is_incompatible():
    resposta = compatibility_service.check(
        CompatibilityQuery(project_id="projeto-fantasma", capability="risk_analysis")
    )
    assert resposta.status is CompatibilityStatus.INCOMPATIBLE
    assert "PROJECT_NOT_REGISTERED" in resposta.blocking


def test_a_project_that_does_not_declare_the_capability_is_incompatible():
    """Quem decide é o manifesto real, não uma tabela neste módulo."""
    resposta = compatibility_service.check(
        CompatibilityQuery(project_id="structa", capability="risk_analysis")
    )
    assert resposta.status is CompatibilityStatus.INCOMPATIBLE
    assert "CAPABILITY_NOT_DECLARED" in resposta.blocking


def test_an_unrecognised_capability_is_unknown_not_incompatible():
    resposta = compatibility_service.check(
        CompatibilityQuery(project_id="pedrocore", capability="capability-do-futuro")
    )
    assert resposta.status is CompatibilityStatus.UNKNOWN
    assert "CAPABILITY_UNKNOWN" in resposta.warnings


def test_an_unknown_contract_version_blocks_the_combination():
    resposta = compatibility_service.check(
        CompatibilityQuery(
            project_id="pedrocore",
            capability="risk_analysis",
            contract_versions=("pedrocore-risk-request/v99",),
        )
    )
    assert resposta.status is CompatibilityStatus.INCOMPATIBLE
    assert "CONTRACT_VERSION_UNKNOWN" in resposta.blocking


def test_a_frozen_v1_contract_is_supported():
    resposta = compatibility_service.check(
        CompatibilityQuery(
            project_id="pedrocore",
            capability="risk_analysis",
            contract_versions=("pedrocore-risk-request/v1",),
        )
    )
    assert resposta.status is CompatibilityStatus.SUPPORTED


def test_an_unsupported_sdk_version_blocks():
    resposta = compatibility_service.check(
        CompatibilityQuery(
            project_id="pedrocore", capability="risk_analysis", sdk_version="0.1.0"
        )
    )
    assert "SDK_VERSION_UNSUPPORTED" in resposta.blocking


def test_a_model_that_is_not_promoted_is_not_usable():
    entrada = _register()
    resposta = compatibility_service.check(
        CompatibilityQuery(
            project_id="pedrocore",
            capability="risk_analysis",
            provider_model=entrada.model_key,
        )
    )
    assert resposta.status is CompatibilityStatus.INCOMPATIBLE


def test_the_answer_shows_its_work_dimension_by_dimension():
    """Um INCOMPATIBLE sem dizer o quê obriga a adivinhar."""
    resposta = compatibility_service.check(
        CompatibilityQuery(project_id="structa", capability="risk_analysis")
    )
    assert resposta.findings
    for achado in resposta.findings:
        assert achado.explanation and achado.reason_code


def test_the_matrix_holds_no_per_project_table():
    """Consumidor novo é atendido por existir no manifesto, não por editar isto."""
    import ast
    import inspect

    from app.modules.compatibility import service as modulo

    arvore = ast.parse(inspect.getsource(modulo))
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            no.body = [
                item
                for item in no.body
                if not (
                    isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
                )
            ]
    codigo = ast.unparse(arvore).lower()
    for nome in ("finguard", "structa", "elyra", "rivvo", "orlabyte"):
        assert nome not in codigo


# ===========================================================================
# E1 — Consumer SDK
# ===========================================================================


class _Transport:
    """Transporte de teste: registra o que foi enviado e devolve o programado."""

    def __init__(self, *respostas: Response | Exception) -> None:
        self.respostas = list(respostas)
        self.chamadas: list[tuple[str, str, dict[str, str], dict | None]] = []

    def __call__(self, method, url, headers, body):
        self.chamadas.append((method, url, dict(headers), body))
        resultado = self.respostas.pop(0) if self.respostas else Response(200, {})
        if isinstance(resultado, Exception):
            raise resultado
        return resultado


def _config(**kw) -> PedroCoreConfig:
    valores = dict(
        base_url="https://core.local",
        api_key="chave-sintetica-de-teste",
        project_id="pedrocore",
        producer="pedrocore-ci",
        backoff_seconds=0.0,
    )
    valores.update(kw)
    return PedroCoreConfig(**valores)


def _client(transport, **kw) -> PedroCoreClient:
    return PedroCoreClient(_config(**kw), transport, sleep=lambda _s: None)


@pytest.mark.parametrize(
    "campo,valor", [("base_url", ""), ("api_key", "  "), ("project_id", "")]
)
def test_the_sdk_refuses_incomplete_configuration_at_construction(campo, valor):
    """Falhar ao construir é melhor que falhar na primeira chamada real."""
    with pytest.raises(PedroCoreConfigError):
        _config(**{campo: valor})


def test_the_sdk_never_reads_configuration_from_the_environment(monkeypatch):
    monkeypatch.setenv("PEDROCORE_API_KEY", "vazado")
    transporte = _Transport(Response(200, {"status": "ok"}))
    cliente = _client(transporte)
    cliente.health()
    assert transporte.chamadas[0][2]["X-Veltrix-Api-Key"] == "chave-sintetica-de-teste"


def test_every_request_carries_identity_and_sdk_version():
    transporte = _Transport(Response(200, {}))
    _client(transporte).health()
    _, _, headers, _ = transporte.chamadas[0]
    assert headers["X-Veltrix-Api-Key"]
    assert SDK_VERSION in headers["X-Veltrix-SDK"]


def test_a_write_carries_a_content_derived_idempotency_key():
    """Um retry precisa levar a MESMA chave, senão a idempotência não acontece."""
    transporte = _Transport(Response(200, {}), Response(200, {}))
    cliente = _client(transporte)
    payload = {"contract_version": "pedrocore-risk-request/v1", "request_id": "a"}
    cliente.analyze_risk(payload)
    cliente.analyze_risk(payload)
    primeira = transporte.chamadas[0][2]["X-Veltrix-Idempotency-Key"]
    segunda = transporte.chamadas[1][2]["X-Veltrix-Idempotency-Key"]
    assert primeira == segunda


def test_a_different_payload_gets_a_different_idempotency_key():
    assert idempotency_key({"a": 1}) != idempotency_key({"a": 2})


def test_the_key_ignores_field_order():
    assert idempotency_key({"a": 1, "b": 2}) == idempotency_key({"b": 2, "a": 1})


def test_a_5xx_is_retried_and_can_succeed():
    transporte = _Transport(Response(503, {}), Response(200, {"status": "ok"}))
    resposta = _client(transporte).health()
    assert resposta.ok
    assert len(transporte.chamadas) == 2


def test_a_4xx_is_never_retried():
    """Insistir num pedido errado não conserta o pedido."""
    transporte = _Transport(Response(403, {"error_code": "CALLER_FORBIDDEN"}))
    with pytest.raises(PedroCoreError) as erro:
        _client(transporte).health()
    assert len(transporte.chamadas) == 1
    assert erro.value.status == 403
    assert erro.value.code == "CALLER_FORBIDDEN"


def test_retries_stop_at_the_configured_limit():
    transporte = _Transport(*[Response(503, {}) for _ in range(5)])
    with pytest.raises(PedroCoreError):
        _client(transporte, max_attempts=3).health()
    assert len(transporte.chamadas) == 3


def test_a_transport_failure_is_reported_without_leaking_its_message():
    segredo = "postgresql://user:supersecret@host/db"
    transporte = _Transport(*[ConnectionError(segredo) for _ in range(3)])
    with pytest.raises(PedroCoreError) as erro:
        _client(transporte).health()
    assert segredo not in str(erro.value)
    assert "ConnectionError" in str(erro.value)


def test_an_error_body_is_not_propagated_raw():
    """Corpo de erro é onde string de conexão costuma aparecer."""
    transporte = _Transport(
        Response(500, {"error_code": "X", "trace": "postgresql://u:senha@h/db"})
    )
    with pytest.raises(PedroCoreError) as erro:
        _client(transporte, max_attempts=1).health()
    assert "senha" not in str(erro.value)


def test_the_risk_submission_declares_identity_in_the_envelope():
    transporte = _Transport(Response(200, {}))
    _client(transporte).analyze_risk({"contract_version": "pedrocore-risk-request/v1"})
    _, url, _, body = transporte.chamadas[0]
    assert url.endswith("/api/risk/universal/analyze")
    assert body["producer"] == "pedrocore-ci"
    assert body["project_id"] == "pedrocore"


def test_the_sdk_has_no_knowledge_of_any_specific_consumer():
    """`if project == '...'` no SDK oficial seria dívida em todo consumidor."""
    import ast
    import inspect

    from app.modules.consumer_sdk import client as modulo

    arvore = ast.parse(inspect.getsource(modulo))
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            no.body = [
                item
                for item in no.body
                if not (
                    isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
                )
            ]
    codigo = ast.unparse(arvore).lower()
    for nome in ("finguard", "structa", "elyra", "rivvo", "orlabyte", "replaydock"):
        assert nome not in codigo
