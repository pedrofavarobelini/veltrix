"""Dataset Control Plane (Era 7).

O GATE 7 pede prova de registry, governanca, versionamento, linhagem e
readiness — **mesmo que nenhum dataset treinavel possa ser materializado**.

Esta suite prova exatamente isso. Ela NAO fabrica populacao no store real: o
unico teste que materializa um dataset roda contra um store isolado em memoria,
povoado por candidatos sinteticos declarados como fixtures de contrato. Eles
existem para exercitar split, linhagem e fingerprint — nunca para simular
readiness que o sistema real nao tem.

O estado real do PedroCore continua `DATASET_NOT_READY`, e isso e correto.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.dataset_registry.schemas import (
    DatasetDefinition,
    DatasetScope,
    DatasetStatus,
    DatasetVersion,
    MaterializationRefusal,
    SplitPolicy,
)
from app.modules.dataset_registry.service import (
    DatasetRegistryError,
    dataset_registry_service,
)
from app.modules.training_data.acquisition import training_candidate_service
from app.modules.training_data.schemas import TrainingPurpose, TrainingSourceType

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
ADMIN = "alpha-admin"
PROJECT = "alpha"


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    monkeypatch.setenv("PEDROCORE_TRAINING_DATA_ADMIN_IDS", ADMIN)
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "memory")
    dataset_registry_service.reset()
    training_candidate_service.reset()
    yield
    dataset_registry_service.reset()
    training_candidate_service.reset()


def _admin() -> AuthenticatedCallerContext:
    return AuthenticatedCallerContext(
        credential_id=ADMIN,
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="test",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id=PROJECT,
        allowed_origins=(PROJECT,),
    )


def _definition(dataset_id="ds-1", **overrides) -> DatasetDefinition:
    base = {
        "dataset_id": dataset_id,
        "display_name": "Dataset de avaliação",
        "scope": DatasetScope.PROJECT,
        "project_ids": (PROJECT,),
        "training_purpose": TrainingPurpose.EVALUATION_ONLY,
        "allowed_source_types": (TrainingSourceType.EVIDENCE_RECORD,),
        "created_by": ADMIN,
        "created_at": NOW,
    }
    base.update(overrides)
    return DatasetDefinition(**base)


# ---------------------------------------------------------------------------
# Governanca: definir e livre
# ---------------------------------------------------------------------------


def test_dataset_can_be_defined_before_any_data_exists():
    """A separacao central da Era: governar nao exige fabricar.

    Se definir implicasse materializar, a unica forma de exercitar a governanca
    seria inventar populacao.
    """
    stored = dataset_registry_service.define(_definition(), _admin())
    assert stored.status is DatasetStatus.DEFINED
    assert stored.created_by == ADMIN
    assert dataset_registry_service.get("ds-1") is not None


def test_definition_requires_admin_capability():
    stranger = _admin().model_copy(update={"credential_id": "quem-sou-eu"})
    with pytest.raises(DatasetRegistryError) as error:
        dataset_registry_service.define(_definition(), stranger)
    assert error.value.code == "DATASET_ADMIN_REQUIRED"


def test_duplicate_dataset_id_is_rejected():
    dataset_registry_service.define(_definition(), _admin())
    with pytest.raises(DatasetRegistryError) as error:
        dataset_registry_service.define(_definition(), _admin())
    assert error.value.code == "DATASET_ALREADY_DEFINED"


def test_creator_comes_from_the_credential_not_the_payload():
    stored = dataset_registry_service.define(
        _definition(created_by="quem-eu-disser"), _admin()
    )
    assert stored.created_by == ADMIN


# ---------------------------------------------------------------------------
# Escopo e project slices
# ---------------------------------------------------------------------------


def test_project_scope_requires_exactly_one_project():
    """Um dataset `project` com tres projetos seria cross-project sem revisao."""
    with pytest.raises(ValueError, match="exatamente um project_id"):
        _definition(project_ids=("alpha", "beta"))


def test_cross_project_scope_requires_at_least_two_projects():
    """Juntar projetos e decisao de privacidade: precisa ser declarada."""
    with pytest.raises(ValueError, match="ao menos dois project_id"):
        _definition(scope=DatasetScope.CROSS_PROJECT, project_ids=("alpha",))


def test_cross_project_dataset_is_valid_when_declared():
    definition = _definition(
        scope=DatasetScope.CROSS_PROJECT, project_ids=("alpha", "beta")
    )
    assert definition.scope is DatasetScope.CROSS_PROJECT
    assert len(definition.project_ids) == 2


# ---------------------------------------------------------------------------
# Split policy
# ---------------------------------------------------------------------------


def test_split_fractions_must_sum_to_one():
    """Resto silencioso seria dado autorizado que nao entra em split nenhum."""
    with pytest.raises(ValueError, match="somar 1.0"):
        SplitPolicy(train=0.7, validation=0.1, test=0.1)


def test_default_split_policy_is_valid_and_groups_by_fingerprint():
    policy = SplitPolicy()
    assert policy.train + policy.validation + policy.test == pytest.approx(1.0)
    assert policy.group_by_fingerprint is True


# ---------------------------------------------------------------------------
# Readiness governa a materializacao
# ---------------------------------------------------------------------------


def test_materialization_is_refused_while_the_population_is_not_ready():
    """O caminho REAL do PedroCore hoje — e o resultado correto.

    A recusa vem com os blockers para que a acao seja obvia: falta populacao
    autorizada, nao configuracao.
    """
    dataset_registry_service.define(_definition(), _admin())
    result = dataset_registry_service.materialize("ds-1", _admin())
    assert isinstance(result, MaterializationRefusal)
    assert result.readiness == "DATASET_NOT_READY"
    assert result.blocker_codes
    assert result.canonical_dataset_created is False
    assert result.training_started is False


def test_refusal_does_not_create_a_partial_dataset():
    """Nada de dataset parcial "so para nao voltar vazio"."""
    dataset_registry_service.define(_definition(), _admin())
    dataset_registry_service.materialize("ds-1", _admin())
    assert dataset_registry_service.versions("ds-1") == []
    assert dataset_registry_service.get("ds-1").status is DatasetStatus.DEFINED


def test_materialization_requires_a_defined_dataset():
    with pytest.raises(DatasetRegistryError) as error:
        dataset_registry_service.materialize("nao-existe", _admin())
    assert error.value.code == "DATASET_NOT_DEFINED"


def test_materialization_requires_admin_capability():
    dataset_registry_service.define(_definition(), _admin())
    stranger = _admin().model_copy(update={"credential_id": "quem-sou-eu"})
    with pytest.raises(DatasetRegistryError) as error:
        dataset_registry_service.materialize("ds-1", stranger)
    assert error.value.code == "DATASET_ADMIN_REQUIRED"


def test_readiness_uses_the_learning_plane_policy_not_a_second_one(monkeypatch):
    """Um segundo criterio aqui seria porta lateral para o mesmo dado."""
    calls: list[str] = []
    real = training_candidate_service.readiness

    def spy(*, project_id, **kwargs):
        calls.append(project_id)
        return real(project_id=project_id, **kwargs)

    monkeypatch.setattr(training_candidate_service, "readiness", spy)
    dataset_registry_service.define(_definition(), _admin())
    dataset_registry_service.materialize("ds-1", _admin())
    assert calls == [PROJECT]


# ---------------------------------------------------------------------------
# Versionamento, linhagem e split — com populacao ISOLADA de fixtures
# ---------------------------------------------------------------------------


def _materialize_with_synthetic_population(monkeypatch, count: int = 40):
    """Materializa contra candidatos sinteticos, em store isolado.

    Estes candidatos NAO entram no store real e nao alteram a readiness do
    PedroCore. Existem para exercitar split, linhagem e fingerprint, que de
    outra forma so poderiam ser testados fabricando populacao real — que e
    exatamente o que a Era proibe.
    """
    from app.modules.training_data.schemas import (
        CandidateLifecycle,
        EligibilityDecision,
        PrivacyClassification,
        TrainingCandidateRecord,
    )

    records = [
        TrainingCandidateRecord(
            # O id segue o padrao real do Learning Plane; a fixture nao
            # afrouxa formato so para ficar legivel.
            candidate_id=f"training-candidate-{index:024x}",
            project_id=PROJECT,
            source_type=TrainingSourceType.EVIDENCE_RECORD,
            source_id=f"evidence-{index:03d}",
            source_reference_hash="sha256:" + f"{index:064x}",
            fingerprint="sha256:" + f"{index + 1000:064x}",
            task_type="evidence_quality_evidence",
            training_purpose=TrainingPurpose.EVALUATION_ONLY,
            lifecycle=CandidateLifecycle.AUTHORIZED,
            eligibility=EligibilityDecision.ELIGIBLE,
            privacy_classification=PrivacyClassification.SAFE,
            policy_version="training-acquisition-v1",
            created_at=NOW,
            updated_at=NOW,
        )
        for index in range(count)
    ]

    monkeypatch.setattr(
        training_candidate_service,
        "readiness",
        lambda *, project_id, **_: type(
            "R", (), {"readiness": "DATASET_READY", "blocker_codes": []}
        )(),
    )
    monkeypatch.setattr(
        training_candidate_service,
        "page",
        lambda *_args, **_kwargs: (records, len(records)),
    )
    dataset_registry_service.define(_definition(), _admin())
    return dataset_registry_service.materialize("ds-1", _admin()), records


def test_materialized_version_records_full_lineage(monkeypatch):
    """Sem linhagem, um modelo treinado seria inauditavel."""
    version, records = _materialize_with_synthetic_population(monkeypatch)
    assert isinstance(version, DatasetVersion)
    assert version.version == 1
    assert version.total_examples == len(records)
    assert len(version.lineage) == len(records)
    entry = version.lineage[0]
    assert entry.candidate_id.startswith("training-candidate-")
    assert entry.authorization_policy_version == "training-acquisition-v1"
    assert entry.split in {"train", "validation", "test"}


def test_split_counts_match_the_total(monkeypatch):
    version, _ = _materialize_with_synthetic_population(monkeypatch)
    assert (
        version.train_examples + version.validation_examples + version.test_examples
        == version.total_examples
    )


def test_split_is_deterministic_across_materializations(monkeypatch):
    """Sem determinismo, duas materializacoes dariam metricas incomparaveis."""
    first, _ = _materialize_with_synthetic_population(monkeypatch)
    dataset_registry_service.reset()
    second, _ = _materialize_with_synthetic_population(monkeypatch)
    assert first.content_fingerprint == second.content_fingerprint
    assert [item.split for item in first.lineage] == [
        item.split for item in second.lineage
    ]


def test_identical_fingerprints_never_land_on_opposite_sides(monkeypatch):
    """O vazamento classico treino/validacao, impedido pela chave do split."""
    from app.modules.dataset_registry.service import _split_for

    policy = SplitPolicy()
    duplicated = "sha256:" + "e" * 64
    assert _split_for(duplicated, policy.seed, policy) == _split_for(
        duplicated, policy.seed, policy
    )


def test_materialization_marks_the_definition_and_increments_versions(monkeypatch):
    version, _ = _materialize_with_synthetic_population(monkeypatch)
    assert dataset_registry_service.get("ds-1").status is DatasetStatus.MATERIALIZED
    second = dataset_registry_service.materialize("ds-1", _admin())
    assert second.version == 2
    assert len(dataset_registry_service.versions("ds-1")) == 2
    assert second.content_fingerprint == version.content_fingerprint


def test_scope_filters_out_candidates_of_other_purposes(monkeypatch):
    """Quatro filtros, nao um: cada um cobre uma decisao diferente."""
    _, records = _materialize_with_synthetic_population(monkeypatch, count=5)
    dataset_registry_service.reset()
    monkeypatch.setattr(
        training_candidate_service,
        "page",
        lambda *_args, **_kwargs: (
            [
                item.model_copy(
                    update={"source_type": TrainingSourceType.HUMAN_FEEDBACK}
                )
                for item in records
            ],
            len(records),
        ),
    )
    dataset_registry_service.define(_definition(), _admin())
    result = dataset_registry_service.materialize("ds-1", _admin())
    assert isinstance(result, MaterializationRefusal)
    assert result.blocker_codes == ["NO_AUTHORIZED_CANDIDATES_IN_SCOPE"]


# ---------------------------------------------------------------------------
# Estado real do PedroCore
# ---------------------------------------------------------------------------


def test_real_pedrocore_population_remains_not_ready():
    """A Era 7 nao fabricou populacao — e este teste e a prova."""
    report = training_candidate_service.readiness(project_id=PROJECT)
    assert report.readiness == "DATASET_NOT_READY"
    assert report.canonical_dataset_created is False
    assert report.training_started is False
