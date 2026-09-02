"""Durabilidade das registries de plataforma, provada contra PostgreSQL real.

A pergunta que estes casos respondem
------------------------------------

    O que a plataforma sabia ontem, ela ainda sabe depois de um restart?

Importa mais do que parece: a promocao de modelo EXIGE evidencia de avaliacao.
Se a avaliacao some no restart, o registry passa a recusar promocoes legitimas
— ou, pior, alguem promove de novo sem saber que ja promoveu.

Sem `PEDROCORE_TEST_POSTGRES_URL` os casos de banco ficam `skip`. Um PASS sem
banco nao seria prova de durabilidade nenhuma.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.env_compat import (
    AmbiguityPolicy,
    AmbiguousEnvironmentError,
    deprecation_notice,
    legacy_name,
    resolve,
)
from app.modules.asset_registry.schemas import AssetKind, AssetStatus
from app.modules.asset_registry.service import asset_registry_service
from app.modules.evaluation_plane.schemas import (
    EvaluationMetric,
    EvaluationSubject,
    EvaluationSubjectKind,
)
from app.modules.evaluation_plane.service import evaluation_plane_service
from app.modules.model_registry.schemas import ModelCapability, ModelStatus
from app.modules.model_registry.service import (
    ModelRegistryError,
    model_registry_service,
)
from app.modules.platform_persistence.repository import (
    FLAG_PLATFORM_DATABASE_URL,
    FLAG_PLATFORM_PERSISTENCE,
    InMemoryPlatformRepository,
    PlatformRepositoryConfigurationError,
    PostgreSQLPlatformRepository,
    build_platform_repository,
    platform_persistence_mode,
)
from app.modules.platform_persistence.service import platform_persistence_service

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
PROJECT = "pedrocore"


@pytest.fixture(autouse=True)
def limpa(monkeypatch):
    monkeypatch.delenv(FLAG_PLATFORM_PERSISTENCE, raising=False)
    monkeypatch.delenv(legacy_name(FLAG_PLATFORM_PERSISTENCE), raising=False)
    monkeypatch.delenv(FLAG_PLATFORM_DATABASE_URL, raising=False)
    monkeypatch.delenv(legacy_name(FLAG_PLATFORM_DATABASE_URL), raising=False)
    platform_persistence_service.reset()
    model_registry_service.reset()
    asset_registry_service.reset()
    evaluation_plane_service.reset()
    yield
    platform_persistence_service.reset()
    model_registry_service.reset()
    asset_registry_service.reset()
    evaluation_plane_service.reset()


# ===========================================================================
# Compatibilidade de variaveis de ambiente
# ===========================================================================


def test_the_canonical_variable_is_read():
    assert resolve("VELTRIX_X", environ={"VELTRIX_X": "novo"}) == "novo"


def test_the_legacy_variable_still_works():
    """Quebrar instalação existente seria a pior forma de renomear."""
    assert resolve("VELTRIX_X", environ={"PEDROCORE_X": "velho"}) == "velho"


def test_the_canonical_wins_when_both_agree():
    ambiente = {"VELTRIX_X": "igual", "PEDROCORE_X": "igual"}
    assert resolve("VELTRIX_X", environ=ambiente) == "igual"


def test_a_conflict_is_refused_instead_of_silently_chosen():
    """Escolher em silêncio seria decidir por quem configurou."""
    ambiente = {"VELTRIX_X": "a", "PEDROCORE_X": "b"}
    with pytest.raises(AmbiguousEnvironmentError) as erro:
        resolve("VELTRIX_X", environ=ambiente)
    assert "ambígua" in str(erro.value)


def test_a_conflict_never_shows_the_values():
    """Mensagem de configuração é lida em log, e log é onde segredo vaza."""
    ambiente = {"VELTRIX_KEY": "segredo-novo", "PEDROCORE_KEY": "segredo-velho"}
    with pytest.raises(AmbiguousEnvironmentError) as erro:
        resolve("VELTRIX_KEY", environ=ambiente)
    mensagem = str(erro.value)
    assert "segredo-novo" not in mensagem and "segredo-velho" not in mensagem


def test_a_non_critical_conflict_can_prefer_the_canonical():
    ambiente = {"VELTRIX_X": "novo", "PEDROCORE_X": "velho"}
    assert (
        resolve("VELTRIX_X", environ=ambiente, policy=AmbiguityPolicy.PREFER_CANONICAL)
        == "novo"
    )


def test_absence_returns_the_default():
    assert resolve("VELTRIX_X", default="padrao", environ={}) == "padrao"


def test_using_only_the_legacy_name_produces_a_deprecation_notice():
    aviso = deprecation_notice("VELTRIX_X", environ={"PEDROCORE_X": "v"})
    assert aviso and "PEDROCORE_X" in aviso and "VELTRIX_X" in aviso


def test_using_the_canonical_name_produces_no_notice():
    assert deprecation_notice("VELTRIX_X", environ={"VELTRIX_X": "v"}) is None


# ===========================================================================
# Configuracao da persistencia
# ===========================================================================


def test_persistence_is_off_by_default():
    assert platform_persistence_mode() == "off"
    assert build_platform_repository() is None


def test_an_invalid_mode_fails_instead_of_falling_back_to_off(monkeypatch):
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "talvez")
    with pytest.raises(PlatformRepositoryConfigurationError):
        platform_persistence_mode()


def test_postgresql_mode_without_a_url_is_refused(monkeypatch):
    """Cair para memória em silêncio perderia promoção sem avisar."""
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "postgresql")
    monkeypatch.delenv("PEDROCORE_TEST_POSTGRES_URL", raising=False)
    with pytest.raises(PlatformRepositoryConfigurationError) as erro:
        build_platform_repository()
    assert "não há persistência" in str(erro.value)


def test_the_legacy_flag_still_enables_persistence(monkeypatch):
    monkeypatch.setenv(legacy_name(FLAG_PLATFORM_PERSISTENCE), "memory")
    assert platform_persistence_mode() == "memory"
    assert isinstance(build_platform_repository(), InMemoryPlatformRepository)


def test_memory_mode_is_enabled_but_not_durable(monkeypatch):
    """Ligado e durável são coisas diferentes, e o serviço as separa."""
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "memory")
    assert platform_persistence_service.enabled() is True
    assert platform_persistence_service.durable() is False


# ===========================================================================
# Reidratacao com store em memoria
# ===========================================================================


def _register_and_promote(evaluation_id="eval-durability"):
    entrada = model_registry_service.register(
        provider="anthropic",
        model_name="claude-sonnet",
        model_version="5",
        capabilities=(ModelCapability.TEXT,),
        now=NOW,
    )
    for alvo, ev in (
        (ModelStatus.CANDIDATE, None),
        (ModelStatus.EVALUATING, None),
        (ModelStatus.APPROVED, evaluation_id),
        (ModelStatus.PROMOTED, evaluation_id),
    ):
        model_registry_service.transition(
            entrada.model_key, alvo, reason="passo", actor="ci", evaluation_id=ev, now=NOW
        )
    return entrada.model_key


def test_a_promoted_model_survives_a_service_restart(monkeypatch):
    """Restart não pode apagar que um modelo já foi promovido."""
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "memory")
    store = platform_persistence_service.repository()
    chave = _register_and_promote()

    # "Restart": o servico esquece tudo e volta a ligar no MESMO store.
    model_registry_service.reset()
    model_registry_service.set_repository(store)

    revivido = model_registry_service.find(chave)
    assert revivido is not None
    assert revivido.status is ModelStatus.PROMOTED
    assert revivido.promoted_at == NOW


def test_the_transition_history_survives_a_restart(monkeypatch):
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "memory")
    store = platform_persistence_service.repository()
    chave = _register_and_promote()

    model_registry_service.reset()
    model_registry_service.set_repository(store)
    assert len(model_registry_service.history(chave)) == 4


def test_the_active_asset_version_survives_a_restart(monkeypatch):
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "memory")
    store = platform_persistence_service.repository()

    asset_registry_service.publish(
        asset_id="assistant.system",
        kind=AssetKind.SYSTEM_PROMPT,
        content="Primeira versão.",
        provenance="veltrix/core",
        author="ci",
        change_reason="inicial",
        now=NOW,
    )
    asset_registry_service.activate("assistant.system", 1)

    asset_registry_service.reset()
    asset_registry_service.set_repository(store)

    ativo = asset_registry_service.active_for("assistant.system")
    assert ativo is not None and ativo.version == 1
    assert ativo.status is AssetStatus.ACTIVE


def test_evaluation_evidence_survives_a_restart(monkeypatch):
    """Sem isto, o registry recusaria promoção legítima após um restart."""
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "memory")
    store = platform_persistence_service.repository()

    registro = evaluation_plane_service.record(
        subject=EvaluationSubject(
            kind=EvaluationSubjectKind.MODEL, subject_id="anthropic:claude-sonnet:5"
        ),
        suite="qa",
        suite_version="1.0",
        environment="test",
        project_id=PROJECT,
        producer="ci",
        dataset_id="ds-1",
        metrics=(EvaluationMetric(name="acuracia", value=0.9, unit="ratio", sample_size=50),),
        now=NOW,
    )

    evaluation_plane_service.reset()
    evaluation_plane_service.set_repository(store)

    assert evaluation_plane_service.get(PROJECT, registro.evaluation_id) is not None
    assert evaluation_plane_service.promotion_evidence(
        PROJECT, "anthropic:claude-sonnet:5"
    ) == [registro.evaluation_id]


def test_rehydration_does_not_duplicate_what_is_already_loaded(monkeypatch):
    monkeypatch.setenv(FLAG_PLATFORM_PERSISTENCE, "memory")
    store = platform_persistence_service.repository()
    chave = _register_and_promote()

    model_registry_service.set_repository(store)
    model_registry_service.find(chave)
    model_registry_service.find(chave)
    assert len(model_registry_service.list()) == 1


# ===========================================================================
# PostgreSQL real
# ===========================================================================


@pytest.fixture
def postgres_url():
    """URL de teste real. Sem ela, os casos abaixo ficam `skip`.

    Nao ha simulacao de PostgreSQL aqui: um duble provaria que o duble
    funciona.
    """
    from app.modules.report_memory.repository import apply_postgresql_migrations

    valor = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not valor:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    apply_postgresql_migrations(valor, Path(__file__).resolve().parents[1] / "migrations")
    repositorio = PostgreSQLPlatformRepository(valor)
    repositorio.clear()
    yield valor
    repositorio.clear()


def test_postgresql_migration_creates_the_platform_tables(postgres_url):
    """A migration 0011 e aplicada pelo runner ja existente."""
    import psycopg

    with psycopg.connect(postgres_url) as conexao:
        linhas = conexao.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_name IN (
                'pedrocore_model_entries', 'pedrocore_model_transitions',
                'pedrocore_asset_versions', 'pedrocore_evaluation_records'
            )
            """
        ).fetchall()
    assert len(linhas) == 4


def test_postgresql_persists_and_reloads_a_promoted_model(postgres_url):
    store = PostgreSQLPlatformRepository(postgres_url)
    model_registry_service.set_repository(store)
    chave = _register_and_promote()

    # Instancia nova do repositorio: durabilidade de verdade, nao cache.
    model_registry_service.reset()
    model_registry_service.set_repository(PostgreSQLPlatformRepository(postgres_url))

    revivido = model_registry_service.find(chave)
    assert revivido is not None and revivido.status is ModelStatus.PROMOTED
    assert "eval-durability" in revivido.evaluation_ids


def test_postgresql_is_idempotent_for_the_same_model(postgres_url):
    store = PostgreSQLPlatformRepository(postgres_url)
    model_registry_service.set_repository(store)
    _register_and_promote()
    _register_and_promote.__doc__  # noqa: B018 - legibilidade

    # Regravar o mesmo estado nao cria uma segunda linha.
    entrada = model_registry_service.list()[0]
    store.save_model(entrada)
    store.save_model(entrada)
    assert len(PostgreSQLPlatformRepository(postgres_url).load_models()) == 1


def test_postgresql_refuses_a_promoted_model_without_evidence(postgres_url):
    """A guarda vive no schema E no banco: um INSERT direto também esbarra."""
    import psycopg

    with psycopg.connect(postgres_url) as conexao:
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute(
                """
                INSERT INTO pedrocore_model_entries (
                    model_key, provider, model_name, model_version,
                    registry_version, status, evaluation_ids, created_at
                ) VALUES (
                    'forjado:modelo:1', 'p', 'm', '1', 'model-registry-v1',
                    'PROMOTED', '[]'::jsonb, NOW()
                )
                """
            )


def test_postgresql_allows_only_one_active_asset_version(postgres_url):
    """Duas ativas seria pior que nenhuma: ninguém saberia qual rodou."""
    import psycopg

    store = PostgreSQLPlatformRepository(postgres_url)
    asset_registry_service.set_repository(store)
    asset_registry_service.publish(
        asset_id="assistant.system",
        kind=AssetKind.SYSTEM_PROMPT,
        content="Primeira.",
        provenance="veltrix/core",
        author="ci",
        change_reason="inicial",
        now=NOW,
    )
    asset_registry_service.activate("assistant.system", 1)

    with psycopg.connect(postgres_url) as conexao:
        with pytest.raises(psycopg.errors.UniqueViolation):
            conexao.execute(
                """
                INSERT INTO pedrocore_asset_versions (
                    asset_id, version, registry_version, kind, status, content,
                    content_hash, provenance, author, change_reason, created_at
                ) VALUES (
                    'assistant.system', 99, 'asset-registry-v1', 'system_prompt',
                    'ACTIVE', 'outra', 'sha256:' || repeat('a', 64), 'p', 'a',
                    'forjada', NOW()
                )
                """
            )


def test_postgresql_refuses_metrics_without_a_dataset(postgres_url):
    import psycopg

    with psycopg.connect(postgres_url) as conexao:
        with pytest.raises(psycopg.errors.CheckViolation):
            conexao.execute(
                """
                INSERT INTO pedrocore_evaluation_records (
                    evaluation_id, project_id, plane_version, subject_kind,
                    subject_id, suite, suite_version, environment, producer,
                    status, metrics, evaluated_at
                ) VALUES (
                    'eval_forjado', 'alpha', 'evaluation-plane-v2', 'model',
                    's', 'suite', '1', 'test', 'ci', 'DATASET_NOT_READY',
                    '[{"name":"x","value":1,"unit":"u","sample_size":1,
                       "higher_is_better":true}]'::jsonb, NOW()
                )
                """
            )


def test_postgresql_isolates_evaluations_by_project(postgres_url):
    """Isolamento é chave composta, garantido pelo banco."""
    store = PostgreSQLPlatformRepository(postgres_url)
    evaluation_plane_service.set_repository(store)
    for projeto in ("alpha", "beta"):
        evaluation_plane_service.record(
            subject=EvaluationSubject(
                kind=EvaluationSubjectKind.MODEL, subject_id="modelo-x"
            ),
            suite="qa",
            suite_version="1.0",
            environment="test",
            project_id=projeto,
            producer="ci",
            dataset_id="ds-1",
            metrics=(
                EvaluationMetric(name="a", value=1.0, unit="u", sample_size=10),
            ),
            now=NOW,
        )

    evaluation_plane_service.reset()
    evaluation_plane_service.set_repository(PostgreSQLPlatformRepository(postgres_url))
    assert len(evaluation_plane_service.for_subject("alpha", "modelo-x")) == 1
    assert len(evaluation_plane_service.for_subject("beta", "modelo-x")) == 1


def test_postgresql_asset_history_survives_reconnection(postgres_url):
    store = PostgreSQLPlatformRepository(postgres_url)
    asset_registry_service.set_repository(store)
    for texto, motivo in (("Primeira.", "inicial"), ("Segunda.", "ajuste")):
        asset_registry_service.publish(
            asset_id="assistant.system",
            kind=AssetKind.SYSTEM_PROMPT,
            content=texto,
            provenance="veltrix/core",
            author="ci",
            change_reason=motivo,
            now=NOW,
        )
    asset_registry_service.activate("assistant.system", 2)

    asset_registry_service.reset()
    asset_registry_service.set_repository(PostgreSQLPlatformRepository(postgres_url))
    registro = asset_registry_service.record("assistant.system")
    assert len(registro.versions) == 2
    assert asset_registry_service.active_for("assistant.system").version == 2


def test_an_unreachable_database_fails_instead_of_becoming_memory():
    """Banco indisponível NÃO vira memória: o chamador precisa saber."""
    store = PostgreSQLPlatformRepository(
        "postgresql://ninguem:ninguem@127.0.0.1:1/inexistente"
    )
    with pytest.raises(Exception) as erro:
        store.load_models()
    assert "indisponível" in str(erro.value)


def test_promotion_after_a_restart_still_requires_evidence(postgres_url):
    """A guarda não afrouxa por o registry ter sido reidratado."""
    store = PostgreSQLPlatformRepository(postgres_url)
    model_registry_service.set_repository(store)
    entrada = model_registry_service.register(
        provider="openai", model_name="gpt", model_version="1", now=NOW
    )
    model_registry_service.transition(
        entrada.model_key, ModelStatus.CANDIDATE, reason="fila", actor="ci", now=NOW
    )
    model_registry_service.transition(
        entrada.model_key, ModelStatus.EVALUATING, reason="medindo", actor="ci", now=NOW
    )

    model_registry_service.reset()
    model_registry_service.set_repository(PostgreSQLPlatformRepository(postgres_url))

    with pytest.raises(ModelRegistryError) as erro:
        model_registry_service.transition(
            entrada.model_key, ModelStatus.APPROVED, reason="sem prova", actor="ci"
        )
    assert "evidência" in str(erro.value)


# ===========================================================================
# Compatibilidade do cabecalho de credencial
# ===========================================================================


def test_the_legacy_credential_header_still_authenticates():
    """Trocar sem alias quebraria os cinco consumidores de uma vez.

    E o erro apareceria como 401, que parece problema de credencial e nao de
    rename — o pior sintoma possivel para diagnosticar.
    """
    from starlette.datastructures import Headers

    from app.modules.caller_identity.technical_api import (
        API_KEY_HEADER,
        LEGACY_API_KEY_HEADER,
        read_api_key,
    )

    class _Request:
        def __init__(self, headers):
            self.headers = Headers(headers)

    assert API_KEY_HEADER == "X-Veltrix-Api-Key"
    assert LEGACY_API_KEY_HEADER == "X-PedroCore-Api-Key"
    assert read_api_key(_Request({LEGACY_API_KEY_HEADER: "chave"})) == "chave"
    assert read_api_key(_Request({API_KEY_HEADER: "chave"})) == "chave"


def test_two_conflicting_credential_headers_are_refused():
    """Preferir um em silêncio faria credencial revogada continuar valendo."""
    from starlette.datastructures import Headers

    from app.modules.caller_identity.technical_api import (
        API_KEY_HEADER,
        LEGACY_API_KEY_HEADER,
        read_api_key,
    )

    class _Request:
        def __init__(self, headers):
            self.headers = Headers(headers)

    assert (
        read_api_key(
            _Request({API_KEY_HEADER: "nova", LEGACY_API_KEY_HEADER: "revogada"})
        )
        is None
    )


def test_the_two_credential_headers_are_actually_different():
    """Guarda contra o erro que este rename já cometeu uma vez.

    Um replace amplo de prosa atingiu o literal do cabecalho legado e o deixou
    identico ao canonico. O alias continuou existindo no codigo e parou de
    existir na pratica: 373 testes caíram de uma vez, todos com 401.
    """
    from app.modules.caller_identity.technical_api import (
        API_KEY_HEADER,
        LEGACY_API_KEY_HEADER,
    )

    assert API_KEY_HEADER != LEGACY_API_KEY_HEADER
    assert "Veltrix" in API_KEY_HEADER
    assert "PedroCore" in LEGACY_API_KEY_HEADER
