"""Paridade do contrato `elyra-multimodal/v2` entre Elyra e Veltrix.

## O defeito que esta suite fecha

A Elyra monta o payload; o Veltrix decide se o aceita. Ate aqui as duas pontas
eram verificadas separadamente: a Elyra provava que produzia um objeto valido
segundo a Elyra, e o Veltrix provava que aceitava um objeto valido segundo o
Veltrix. Os dois testes podiam continuar verdes para sempre com os dois lados
incompativeis - e foi exatamente o que aconteceu. A Elyra enviava
`elyra-multimodal/v2`, `signals/v2` e `extractor/v3` para um servico que so
conhecia `v1`, e nenhuma suite dos dois lados viu.

As fixtures lidas aqui NAO sao escritas a mao. Elas sao geradas pelo
`buildMultimodalInput` real da Elyra - o mesmo caminho que uma sessao usa - e
copiadas para ca junto do manifesto de digests. Se a Elyra passar a mandar um
campo, ou deixar de mandar, o arquivo muda; se a copia daqui ficar para tras, o
digest diverge e o teste quebra em vez de validar um payload que a Elyra nao
produz mais.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.elyra_multimodal.schemas import ElyraMultimodalInputV1
from app.modules.elyra_multimodal.schemas_v2 import (
    ELYRA_MULTIMODAL_CONTRACT_VERSION_V2,
    FEATURE_EXTRACTOR_VERSION_V2,
    SIGNALS_SCHEMA_VERSION_V2,
    VISUAL_MODALITIES,
    VISUAL_SIGNAL_NAMES,
    ElyraMultimodalInputV2,
    ElyraMultimodalOutputV2,
)
from app.modules.elyra_multimodal.service import elyra_multimodal_service

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "elyra-multimodal-v2"
MANIFEST = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
FIXTURE_NAMES = sorted(MANIFEST["fixtures"])


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


class TestFixtureIntegrity:
    def test_manifest_declara_as_versoes_da_v2(self) -> None:
        assert MANIFEST["contract"] == ELYRA_MULTIMODAL_CONTRACT_VERSION_V2
        assert MANIFEST["signalsSchemaVersion"] == SIGNALS_SCHEMA_VERSION_V2
        assert MANIFEST["featureExtractorVersion"] == FEATURE_EXTRACTOR_VERSION_V2

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_fixture_corresponde_ao_digest_gerado_pela_elyra(self, name: str) -> None:
        """A protecao contra a falha silenciosa mais provavel.

        Sem ela, alguem copiaria uma fixture antiga para ca e esta suite
        passaria validando um payload que a Elyra nao produz mais - exatamente
        a forma de "verde enganoso" que a incompatibilidade v1/v2 teve.
        """
        raw = (FIXTURE_DIR / f"{name}.json").read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == MANIFEST["fixtures"][name], (
            f"Fixture {name} divergiu do que a Elyra gera. "
            "Regenere na Elyra e copie as duas pontas juntas."
        )


class TestContractParity:
    """O payload da Elyra e aceito SEM adaptacao manual."""

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_veltrix_aceita_o_payload_da_elyra(self, name: str) -> None:
        payload = read_fixture(name)
        # Nenhuma transformacao antes de validar: e o objeto exato que atravessa.
        value = ElyraMultimodalInputV2.model_validate(payload)
        assert value.contract_version == ELYRA_MULTIMODAL_CONTRACT_VERSION_V2
        assert value.session.signals_schema_version == SIGNALS_SCHEMA_VERSION_V2
        assert (
            value.session.feature_extractor_version == FEATURE_EXTRACTOR_VERSION_V2
        )

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_o_schema_v1_nao_aceita_payload_v2(self, name: str) -> None:
        """A prova de que a incompatibilidade era real, e nao cosmetica.

        Se a V1 aceitasse a fixture V2, o blocker teria sido so de nome e
        bastaria trocar strings. Ela nao aceita: os campos novos nao existiam.
        """
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV1.model_validate(read_fixture(name))

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_o_servico_produz_saida_valida_para_cada_fixture(self, name: str) -> None:
        request = ElyraMultimodalInputV2.model_validate(read_fixture(name))
        output = elyra_multimodal_service.deterministic_mock(request, "corr-parity-001")
        assert isinstance(output, ElyraMultimodalOutputV2)

        raw = elyra_multimodal_service.serialize_output(output)
        validation = elyra_multimodal_service.validate_output(
            raw, request, "corr-parity-001"
        )
        assert validation.valid, validation.reason


class TestBackwardCompatibility:
    """A V1 continua aceita. Ganhar a V2 nao pode custar o passado."""

    def test_v1_continua_sendo_validada_pelo_schema_v1(self) -> None:
        v1_payload = {
            "contractVersion": "elyra-multimodal/v1",
            "inputSchemaVersion": "elyra-multimodal-input/v1",
            "operation": "interpret_observable_session_signals",
            "aiInferenceConsent": True,
            "multimodalAnalysisConsent": True,
            "transcriptAnalysisConsent": False,
            "session": {
                "signalsSchemaVersion": "multimodal_signals/v1",
                "featureExtractorVersion": "elyra-signals/v1",
                "sessionKind": "free",
                "capturedResources": ["microphone"],
                "durationMs": 60_000,
                "signals": [
                    {
                        "name": "speech_rate",
                        "value": 120.0,
                        "unit": "words_per_minute",
                        "personalBaselineMean": 118.0,
                        "personalBaselineSamples": 4,
                        "deltaVsPersonalBaseline": 2.0,
                        "status": "available",
                    }
                ],
            },
        }
        value = ElyraMultimodalInputV1.model_validate(v1_payload)
        assert value.contract_version == "elyra-multimodal/v1"

        # E o mock V1 continua produzindo saida V1, sem virar V2 por acidente.
        output = elyra_multimodal_service.deterministic_mock(value, "corr-v1-001")
        assert output.contract_version == "elyra-multimodal/v1"

    def test_v2_nao_e_convertida_silenciosamente_para_v1(self) -> None:
        """Converter perderia cobertura, autorrelato, janela e consentimento
        visual - campos que a V1 nao sabe nomear. Perder em silencio seria pior
        que recusar."""
        request = ElyraMultimodalInputV2.model_validate(read_fixture("full-multimodal"))
        output = elyra_multimodal_service.deterministic_mock(request, "corr-v2-001")
        assert output.contract_version == "elyra-multimodal/v2"
        assert output.source_feature_extractor_version == "elyra-signals/v3"


class TestMinimizedProjection:
    """Nenhuma midia atravessa a fronteira. Teste negativo, por chave."""

    FORBIDDEN_KEYS = {
        "userid", "user_id", "sessionid", "session_id",
        "storage", "bucket", "signedurl", "publicurl",
        "mediaasset", "media_asset", "blob", "pcm", "waveform",
        "audio", "video", "frame", "frames", "image", "thumbnail",
        "landmark", "landmarks", "keypoint", "descriptor", "embedding",
        "apikey", "api_key", "token", "secret", "password", "credential",
        # WER e CER sao medidas de QA privadas da Elyra: como atributo de
        # sessao elas viravam "confianca clinica".
        "wer", "cer", "accuracy", "errorrate",
    }

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_nenhuma_chave_proibida_atravessa(self, name: str) -> None:
        found: list[str] = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key.lower() in self.FORBIDDEN_KEYS:
                        found.append(key)
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(read_fixture(name))
        assert found == [], f"chaves proibidas na projecao: {found}"

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_nenhum_valor_carrega_url_ou_midia(self, name: str) -> None:
        offenders: list[str] = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, str):
                lowered = node.lower()
                if lowered.startswith(("http://", "https://", "data:")):
                    offenders.append(node)
                if any(
                    lowered.endswith(ext)
                    for ext in (".png", ".jpg", ".jpeg", ".webm", ".mp4", ".wav", ".mp3")
                ):
                    offenders.append(node)

        walk(read_fixture(name))
        assert offenders == [], f"valores com midia ou URL: {offenders}"

    def test_sem_consentimento_visual_nada_de_landmark_atravessa(self) -> None:
        payload = read_fixture("camera-without-visual-consent")
        assert payload["visualAnalysisConsent"] is False

        session = payload["session"]
        assert not any(
            signal["name"] in VISUAL_SIGNAL_NAMES for signal in session["signals"]
        )
        assert not any(
            window["signal"] in VISUAL_SIGNAL_NAMES for window in session["windows"]
        )
        # Cobertura visual tambem nao: "rosto observavel por 22 dos 30 minutos"
        # e uma observacao sobre o corpo de quem nao autorizou observacao dele.
        assert not any(
            coverage["modality"] in VISUAL_MODALITIES
            for coverage in session["modalityCoverage"]
        )
        # E o sinal que NAO depende de landmark sobrevive.
        assert any(
            signal["name"] == "movement_frequency" for signal in session["signals"]
        )


class TestContractRejection:
    """Mutacoes que DEVEM derrubar a validacao."""

    def test_campo_obrigatorio_removido_e_recusado(self) -> None:
        """A cobertura por modalidade e obrigatoria, por si.

        A fixture aqui e a `microphone-only` de proposito. Com a
        `full-multimodal`, remover `modalityCoverage` tambem quebra a regra "sinal
        visual precisa da cobertura da sua modalidade" - e o teste passaria pelo
        motivo errado, sem nunca verificar que o campo e exigido. Uma mutacao que
        tornasse `modalityCoverage` opcional sobrevivia exatamente por isso.

        Nesta sessao nao ha sinal visual: se o payload for recusado, foi porque o
        campo e obrigatorio, e por nada mais.
        """
        payload = read_fixture("microphone-only")
        assert not any(
            signal["name"] in VISUAL_SIGNAL_NAMES
            for signal in payload["session"]["signals"]
        )
        del payload["session"]["modalityCoverage"]
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_cobertura_vazia_e_recusada(self) -> None:
        """Lista vazia nao e "sem cobertura declarada": e cobertura ausente.

        Aceita-la deixaria um sinal viajar sem nada dizendo sobre quanto da
        sessao ele descreve - o engano que `PARTIAL_CAPTURE != FULL_CAPTURE`
        existe para fechar.
        """
        payload = read_fixture("microphone-only")
        payload["session"]["modalityCoverage"] = []
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_campo_desconhecido_e_recusado(self) -> None:
        """Schema estrito: um campo a mais pode ser midia com outro nome."""
        payload = read_fixture("full-multimodal")
        payload["session"]["rawAudio"] = "AAAA"
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_sinal_visual_sem_consentimento_visual_e_recusado(self) -> None:
        payload = read_fixture("full-multimodal")
        payload["visualAnalysisConsent"] = False
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_cobertura_visual_sem_consentimento_visual_e_recusada(self) -> None:
        payload = read_fixture("full-multimodal")
        payload["visualAnalysisConsent"] = False
        payload["session"]["signals"] = [
            signal
            for signal in payload["session"]["signals"]
            if signal["name"] not in VISUAL_SIGNAL_NAMES
        ]
        payload["session"]["windows"] = [
            window
            for window in payload["session"]["windows"]
            if window["signal"] not in VISUAL_SIGNAL_NAMES
        ]
        # Sobra so a cobertura visual - e ela sozinha ja e observacao do corpo.
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_transcricao_sem_consentimento_de_transcricao_e_recusada(self) -> None:
        payload = read_fixture("full-multimodal")
        payload["transcriptAnalysisConsent"] = False
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_sinal_nao_capturado_com_valor_e_recusado(self) -> None:
        """NULL nao e zero, e ausencia nao carrega medida."""
        payload = read_fixture("absent-signals")
        payload["session"]["signals"][0]["value"] = 0.0
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_cobertura_maior_que_a_sessao_e_recusada(self) -> None:
        payload = read_fixture("full-multimodal")
        payload["session"]["modalityCoverage"][0]["coverageMs"] = 999_999_9
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)

    def test_modalidade_ausente_com_cobertura_e_recusada(self) -> None:
        payload = read_fixture("full-multimodal")
        for coverage in payload["session"]["modalityCoverage"]:
            if coverage["outcome"] == "absent":
                coverage["coverageMs"] = 1000
        with pytest.raises(ValidationError):
            ElyraMultimodalInputV2.model_validate(payload)


class TestOutputSafety:
    """A saida nao pode afirmar o que a fronteira proibe."""

    def _valid_output(self) -> dict:
        request = ElyraMultimodalInputV2.model_validate(read_fixture("full-multimodal"))
        output = elyra_multimodal_service.deterministic_mock(request, "corr-safety-001")
        return json.loads(elyra_multimodal_service.serialize_output(output))

    def test_safety_declara_todas_as_negativas(self) -> None:
        safety = self._valid_output()["safety"]
        for flag in (
            "diagnosticClaim",
            "prescription",
            "causalClaim",
            "facialEmotionAsFact",
            "fictitiousEmotionPercentage",
            "emotionInferredFromSignal",
            "rawMediaAccessed",
            "populationNormComparison",
            "selfReportContradictedBySignal",
        ):
            assert safety[flag] is False, flag

    def test_safety_com_afirmacao_positiva_e_recusada(self) -> None:
        payload = self._valid_output()
        payload["safety"]["rawMediaAccessed"] = True
        with pytest.raises(ValidationError):
            ElyraMultimodalOutputV2.model_validate(payload)

    def test_observacao_sem_correlacao_e_recusada(self) -> None:
        request = ElyraMultimodalInputV2.model_validate(read_fixture("full-multimodal"))
        raw = json.dumps(self._valid_output())
        validation = elyra_multimodal_service.validate_output(
            raw, request, "corr-outra-001"
        )
        assert not validation.valid

    def test_observacao_ancorada_em_sinal_nao_enviado_e_recusada(self) -> None:
        request = ElyraMultimodalInputV2.model_validate(read_fixture("microphone-only"))
        payload = self._valid_output()
        payload["correlationId"] = "corr-safety-002"
        payload["observations"][0] = {
            "category": "observable_signal",
            # A sessao microphone-only nao enviou nenhum sinal visual.
            "evidencePath": "signals.head_movement_frequency",
            "text": "Observacao sobre um sinal que nunca foi enviado.",
        }
        validation = elyra_multimodal_service.validate_output(
            json.dumps(payload), request, "corr-safety-002"
        )
        assert not validation.valid

    def test_observacao_ancorada_em_autorrelato_ausente_e_recusada(self) -> None:
        request = ElyraMultimodalInputV2.model_validate(
            read_fixture("camera-without-visual-consent")
        )
        assert request.session.self_report is None
        payload = self._valid_output()
        payload["correlationId"] = "corr-safety-003"
        payload["sourceSignalsSchemaVersion"] = SIGNALS_SCHEMA_VERSION_V2
        payload["observations"] = [
            {
                "category": "capture_quality",
                "evidencePath": "selfReport",
                "text": "Observacao sobre um relato que a pessoa nao fez.",
            }
        ]
        validation = elyra_multimodal_service.validate_output(
            json.dumps(payload), request, "corr-safety-003"
        )
        assert not validation.valid

    def test_confianca_recua_quando_a_cobertura_e_parcial(self) -> None:
        """`confidence` altera o que se afirma; nao e rotulo decorativo."""
        full = ElyraMultimodalInputV2.model_validate(read_fixture("full-multimodal"))
        absent = ElyraMultimodalInputV2.model_validate(read_fixture("absent-signals"))

        # full-multimodal tem cobertura visual ausente -> nao pode ser "high".
        assert elyra_multimodal_service.deterministic_mock(full, "c-1").confidence in {
            "low",
            "moderate",
        }
        # absent-signals nao tem nenhum sinal disponivel -> "low".
        assert elyra_multimodal_service.deterministic_mock(absent, "c-2").confidence == "low"
