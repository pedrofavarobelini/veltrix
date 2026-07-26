import asyncio
import os
import time

from app.core.config import settings
from app.modules.caller_identity.schemas import CallerRole
from app.modules.observability.sanitizer import sanitize_text
from app.modules.observability.schemas import GeminiSmokeRequest, GeminiSmokeResponse
from app.modules.observability.service import observability_service
from app.modules.provider_binding.service import provider_binding_service
from app.modules.providers.registry import provider_registry
from app.modules.real_features import service as real_features

SYNTHETIC_PAYLOAD = "PEDROCORE_GEMINI_SMOKE_V1"
SYNTHETIC_PROMPT = "Responda apenas com a palavra OK."
NETWORK_NOTICE = "Esta ação faz uma chamada de rede ao Gemini."
COST_NOTICE = "Esta ação pode gerar custo no provedor configurado."
SAFE_FALLBACK = "A chamada sintética não foi concluída; nenhum dado real foi enviado."


def _environment() -> str:
    return (os.environ.get("APP_ENV") or settings.app_env or "development").strip().lower()


class GeminiSmokeService:
    def _blocked(self, payload: GeminiSmokeRequest, reason: str) -> GeminiSmokeResponse:
        response = GeminiSmokeResponse(
            status="blocked",
            executed=False,
            reason=reason,
            notices=[NETWORK_NOTICE, COST_NOTICE],
        )
        observability_service.record_gemini_smoke(payload, response, 0.0)
        return response

    async def execute(self, payload: GeminiSmokeRequest) -> GeminiSmokeResponse:
        if _environment() in {"prod", "production"}:
            return self._blocked(payload, "Smoke Gemini real bloqueado em produção.")
        if payload.synthetic_payload != SYNTHETIC_PAYLOAD:
            return self._blocked(payload, "Payload inadequado: somente o marcador sintético é aceito.")
        if not (
            payload.confirm_network
            and payload.confirm_possible_cost
            and payload.confirm_key_not_compromised
        ):
            return self._blocked(
                payload,
                "Confirmações de rede, possível custo e integridade da chave são obrigatórias.",
            )
        if not (
            real_features.flag_enabled(real_features.FLAG_RUN_REAL_PROVIDER_TESTS)
            and real_features.flag_enabled(real_features.FLAG_RUN_REAL_GEMINI_TESTS)
        ):
            return self._blocked(payload, "As duas flags opt-in do provider e do Gemini são obrigatórias.")
        if not settings.gemini_api_key:
            return self._blocked(payload, "Credencial externa Gemini ausente; chamada não executada.")

        provider = provider_registry.get("gemini")
        if provider is None or not provider.is_configured:
            return self._blocked(payload, "Provider Gemini indisponível ou não configurado.")
        binding = provider_binding_service.resolve(
            requested_provider="gemini",
            requested_model=None,
            selection_mode="explicit",
            caller_role=CallerRole.TECHNICAL_TOOL,
            task_type="assistant_chat",
        )
        if binding.invalid or binding.model_id is None:
            return self._blocked(
                payload,
                "Binding Gemini sem modelo default explícito, homologado e autorizado.",
            )

        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                provider.generate_response(
                    message=SYNTHETIC_PROMPT,
                    mode="resumido",
                    model=binding.model_id,
                    system_prompt=(
                        "Smoke técnico sintético. Não solicite nem use dados financeiros, "
                        "relatórios, arquivos ou informações do usuário."
                    ),
                ),
                timeout=30.0,
            )
            response = GeminiSmokeResponse(
                status="ok",
                executed=True,
                call_count=1,
                provider=result.provider,
                model=result.model,
                public_response=sanitize_text(result.answer, 500),
                notices=[NETWORK_NOTICE, COST_NOTICE],
            )
        except Exception as exc:
            response = GeminiSmokeResponse(
                status="fallback",
                executed=True,
                call_count=1,
                fallback=True,
                reason=sanitize_text(exc, 500),
                public_response=SAFE_FALLBACK,
                notices=[NETWORK_NOTICE, COST_NOTICE],
            )

        observability_service.record_gemini_smoke(
            payload, response, (time.perf_counter() - started) * 1_000
        )
        return response


gemini_smoke_service = GeminiSmokeService()
