"""Contract Freeze V1 (Era 9).

Por que congelar
----------------

Um contrato publicado deixa de pertencer a quem o escreveu. A partir do momento
em que um consumidor programa contra ele, mudar um campo obrigatorio ou o tipo
de um valor quebra codigo de terceiro — e a quebra aparece na producao DELE,
nao na nossa.

O congelamento nao proibe evolucao. Ele obriga a evolucao a ser DECLARADA:

  - mudanca aditiva (campo opcional com default) nao altera o fingerprint de
    forma que quebre consumidor, mas ainda assim aparece aqui e exige que
    alguem confirme que e mesmo aditiva;
  - mudanca breaking exige `.../v2`, com a v1 mantida ate haver migration path.

Sem este teste, a unica defesa seria alguem lembrar. Com ele, a alteracao de um
contrato V1 falha o build e a conversa acontece antes do merge.

Como atualizar quando a mudanca for legitima
--------------------------------------------

Rodar a suite, ler o fingerprint novo na mensagem de falha, confirmar que a
mudanca e mesmo aditiva (ou criar a v2) e so entao atualizar a constante — com
o motivo no commit. O trabalho manual e o ponto: ele obriga a decisao.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel

from app.modules.universal_contracts.capability_manifest import (
    ProjectCapabilityManifestV1,
)
from app.modules.universal_contracts.envelope import PedroCoreIntegrationEnvelopeV1
from app.modules.universal_contracts.execution_outcome import ExecutionOutcomeV1
from app.modules.universal_contracts.learning_source import LearningSourceV1
from app.modules.universal_contracts.quality_evidence import QualityEvidenceV1
from app.modules.universal_contracts.versioning import (
    CAPABILITY_MANIFEST_V1,
    EXECUTION_OUTCOME_V1,
    INTEGRATION_ENVELOPE_V1,
    LEARNING_SOURCE_V1,
    QUALITY_EVIDENCE_V1,
    ContractVersionStatus,
    version_status,
)

# Fingerprints congelados em 29/08/2026 (Era 9).
FROZEN_V1_SCHEMAS: dict[str, str] = {
    "capability_manifest": "sha256:e4bdfa626e756107edf655af387defafe91e9a16a60cb8f49d3a550bb95e29e6",
    "quality_evidence": "sha256:ee63c68b1f242d91ae1398be0d39408ebe31f7f78f2ca51d4ce25ed2b501e50e",
    "execution_outcome": "sha256:25f62fcf94713bf81ec26c806782c5749439d08aae2c180003f5691abdd0e35c",
    "learning_source": "sha256:77021aec2dce490a8b7eb41cb9f9833322b6044ed91eb3ad9a1bb466a5995da8",
    "integration_envelope": "sha256:5e9a5c35beab6d6f0c3b6b9c20310d0661f936589775c44b6fa20051006780e4",
}

FROZEN_MODELS: dict[str, type[BaseModel]] = {
    "capability_manifest": ProjectCapabilityManifestV1,
    "quality_evidence": QualityEvidenceV1,
    "execution_outcome": ExecutionOutcomeV1,
    "learning_source": LearningSourceV1,
    "integration_envelope": PedroCoreIntegrationEnvelopeV1,
}

FROZEN_VERSION_IDENTIFIERS: dict[str, str] = {
    "capability_manifest": CAPABILITY_MANIFEST_V1,
    "quality_evidence": QUALITY_EVIDENCE_V1,
    "execution_outcome": EXECUTION_OUTCOME_V1,
    "learning_source": LEARNING_SOURCE_V1,
    "integration_envelope": INTEGRATION_ENVELOPE_V1,
}


def _fingerprint(model: type[BaseModel]) -> str:
    schema = json.dumps(model.model_json_schema(), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(schema.encode()).hexdigest()


def test_v1_contract_schemas_are_frozen():
    """Qualquer alteracao de forma em um contrato V1 falha aqui."""
    drifted: list[str] = []
    for name, model in FROZEN_MODELS.items():
        current = _fingerprint(model)
        if current != FROZEN_V1_SCHEMAS[name]:
            drifted.append(f"{name}: esperado {FROZEN_V1_SCHEMAS[name]}, obtido {current}")
    assert not drifted, (
        "Contratos V1 congelados foram alterados:\n  "
        + "\n  ".join(drifted)
        + "\n\nSe a mudança for ADITIVA e compatível, atualize FROZEN_V1_SCHEMAS "
        "explicando o motivo no commit. Se for BREAKING, crie a v2 e mantenha "
        "a v1 até existir migration path."
    )


def test_every_frozen_contract_declares_a_v1_identifier():
    for name, identifier in FROZEN_VERSION_IDENTIFIERS.items():
        assert identifier.endswith("/v1"), name
        assert version_status(identifier) is ContractVersionStatus.SUPPORTED, name


def test_frozen_set_covers_every_published_contract():
    """Um contrato publicado fora deste conjunto nao estaria congelado.

    A cobertura e verificada contra o versionamento, e nao contra uma lista
    escrita a mao aqui — uma lista paralela poderia esquecer o contrato novo.
    """
    from app.modules.universal_contracts.versioning import SUPPORTED_CONTRACT_VERSIONS

    frozen = set(FROZEN_VERSION_IDENTIFIERS.values())
    assert frozen == set(SUPPORTED_CONTRACT_VERSIONS), (
        "Existe contrato suportado que não está congelado (ou vice-versa): "
        f"{sorted(frozen ^ set(SUPPORTED_CONTRACT_VERSIONS))}"
    )


def test_frozen_contracts_forbid_unknown_fields():
    """`extra=forbid` faz parte do congelamento.

    Sem ele, um consumidor poderia enviar campos que o servidor ignora, passar
    a depender deles e quebrar quando alguem finalmente os implementasse com
    outro significado.
    """
    for name, model in FROZEN_MODELS.items():
        assert model.model_config.get("extra") == "forbid", name


def test_learning_source_never_gains_governance_fields():
    """A garantia mais importante do congelamento, afirmada por nome.

    O fingerprint ja pegaria isto, mas a mensagem de erro seria "o schema
    mudou". Este teste diz QUAL fronteira foi cruzada.
    """
    forbidden = {
        "eligibility",
        "authorized",
        "authorization",
        "candidate_id",
        "lifecycle",
        "training_purpose",
        "quality_score",
        "readiness",
        "automatic_collection",
    }
    assert not (set(LearningSourceV1.model_fields) & forbidden)


def test_capability_manifest_never_grants_authorization():
    forbidden = {"authorized", "authorization", "allows_neural_training", "eligibility"}
    assert not (set(ProjectCapabilityManifestV1.model_fields) & forbidden)


def test_quality_evidence_never_gains_an_authoritative_score():
    forbidden = {"quality_score", "trust_score", "approved", "eligibility"}
    assert not (set(QualityEvidenceV1.model_fields) & forbidden)
