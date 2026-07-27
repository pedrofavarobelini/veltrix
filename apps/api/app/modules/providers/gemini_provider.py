"""Adapter Gemini (OUTPUT-BUDGET-CANCELLATION-01).

Mudanças estruturais em relação à versão anterior:

  - cliente ASSÍNCRONO nativo (`client.aio.models.generate_content`), sem
    `asyncio.to_thread`: cancelar a task cancela o `await` de verdade;
  - orçamento explícito de saída via `GenerateContentConfig.max_output_tokens`;
  - timeout de transporte explícito via `HttpOptions.timeout` (milissegundos);
  - lifecycle determinístico: o cliente é fechado em sucesso, erro, timeout e
    cancelamento;
  - `finish_reason` e `usage_metadata` são lidos em vez de descartados;
  - `HttpRetryOptions` NUNCA é configurado — o default do SDK instalado é
    `stop_after_attempt(1)`, ou seja, uma chamada lógica produz no máximo um
    dispatch externo.

Limite honesto e deliberado: fechar a conexão local não prova que a geração
remota parou. Timeout de transporte continua sendo conclusão AMBÍGUA.
"""

from app.core.config import settings
from app.modules.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderExecutionError,
    ProviderOutputRejectedError,
    ProviderResponse,
    ProviderTransportTimeoutError,
    TransportClose,
    normalize_token_count,
)

# `finish_reason` que representa conclusão normal. Ausência de finish_reason
# em resposta não-streaming é aceita quando existe texto utilizável.
FINISH_REASON_STOP = "STOP"
FINISH_REASON_UNSPECIFIED = "FINISH_REASON_UNSPECIFIED"
FINISH_REASON_MAX_TOKENS = "MAX_TOKENS"

_NORMAL_FINISH_REASONS = {FINISH_REASON_STOP, FINISH_REASON_UNSPECIFIED}

TRUNCATED_MESSAGE = (
    "Resposta do provider interrompida pelo orçamento de saída do PedroCore; "
    "conteúdo parcial não é publicado como resposta completa."
)
ABNORMAL_FINISH_MESSAGE = (
    "Provider encerrou a geração por condição anormal; resposta não é "
    "utilizável como conclusão normal."
)
EMPTY_TEXT_MESSAGE = "Gemini respondeu sem texto utilizável."


def _load_genai():
    """Import tardio do SDK, isolado para permitir fake determinístico em teste.

    Os testes substituem apenas o módulo cliente; os tipos continuam sendo os
    tipos REAIS do `google-genai` instalado, para que a asserção sobre
    `GenerateContentConfig` e `HttpOptions` valha contra o SDK de verdade.
    """
    from google import genai
    from google.genai import types as genai_types

    return genai, genai_types


def _is_transport_timeout(error: BaseException) -> bool:
    """Identifica expiração do transporte HTTP, não da espera da orquestração."""
    if isinstance(error, TimeoutError):
        return True
    try:
        import httpx
    except Exception:  # pragma: no cover - httpx é dependência declarada
        return False
    return isinstance(error, httpx.TimeoutException)


def _finish_reason_of(response: object) -> str | None:
    """Extrai o `finish_reason` do primeiro candidato, sem assumir formato."""
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        reason = getattr(candidate, "finish_reason", None)
        if reason is None:
            continue
        return str(getattr(reason, "value", reason)).strip().upper() or None
    return None


def _usage_of(response: object) -> tuple[int | None, int | None, int | None]:
    """Lê `usage_metadata` real; ausência nunca é falha e nunca vira estimativa."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None, None, None

    input_tokens = normalize_token_count(getattr(usage, "prompt_token_count", None))
    output_tokens = normalize_token_count(
        getattr(usage, "candidates_token_count", None)
    )
    total_tokens = normalize_token_count(getattr(usage, "total_token_count", None))

    # `total` legitimamente excede input+output em modelos com raciocínio
    # (thoughts_token_count). Só um total MENOR que a soma é incoerente, e
    # nesse caso preferimos omitir a métrica a publicar um número errado.
    if (
        total_tokens is not None
        and input_tokens is not None
        and output_tokens is not None
        and total_tokens < input_tokens + output_tokens
    ):
        total_tokens = None

    return input_tokens, output_tokens, total_tokens


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    label = "Gemini"
    default_model = settings.gemini_model
    supports_generation_budget = True
    supports_transport_cancellation = True

    @property
    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str,
        system_prompt: str | None = None,
        output_budget: int | None = None,
        transport_timeout_ms: int | None = None,
    ) -> ProviderResponse:
        if not self.is_configured:
            raise ProviderConfigError("GEMINI_API_KEY não configurada.")

        budget = self._validated_budget(output_budget)
        timeout_ms = self._validated_timeout_ms(transport_timeout_ms)

        try:
            genai, genai_types = _load_genai()
        except Exception as error:
            raise ProviderExecutionError(
                f"SDK do Gemini indisponível: {error}"
            ) from error

        prompt = self.build_prompt(message, mode, system_prompt)

        try:
            client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=genai_types.HttpOptions(timeout=timeout_ms),
            )
        except Exception as error:
            raise ProviderExecutionError(
                f"Falha ao preparar o cliente Gemini: {error}"
            ) from error

        try:
            # Nenhum `HttpRetryOptions`: o default do SDK é não repetir.
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(max_output_tokens=budget),
            )
            result = self._normalize(
                response,
                model=model,
                budget=budget,
                timeout_ms=timeout_ms,
            )
        except ProviderExecutionError as error:
            # Inclui truncamento e finish_reason anormal, levantados por
            # `_normalize`. O fechamento é observado e anexado à exceção.
            error.transport_close = await self._aclose(client)
            raise
        except Exception as error:
            close_outcome = await self._aclose(client)
            if _is_transport_timeout(error):
                translated: ProviderExecutionError = ProviderTransportTimeoutError(
                    "Transporte do Gemini expirou antes da conclusão da geração."
                )
            else:
                translated = ProviderExecutionError(
                    f"Falha no GeminiProvider: {error}"
                )
            translated.transport_close = close_outcome
            raise translated from error
        except BaseException:
            # Cancelamento da task: o cliente ainda precisa ser fechado, mas o
            # resultado não chega a ninguém — quem cancelou observa apenas o
            # próprio cancelamento.
            await self._aclose(client)
            raise

        result.transport_close = await self._aclose(client)
        return result

    # ------------------------------------------------------------------
    @staticmethod
    def _validated_budget(output_budget: int | None) -> int:
        """O adapter nunca executa sem orçamento explícito do PedroCore."""
        if (
            isinstance(output_budget, bool)
            or not isinstance(output_budget, int)
            or output_budget <= 0
        ):
            raise ProviderExecutionError(
                "Adapter não pode executar sem orçamento de saída válido "
                "resolvido pelo PedroCore."
            )
        return output_budget

    @staticmethod
    def _validated_timeout_ms(transport_timeout_ms: int | None) -> int:
        """O adapter nunca executa com transporte sem teto temporal."""
        if (
            isinstance(transport_timeout_ms, bool)
            or not isinstance(transport_timeout_ms, int)
            or transport_timeout_ms <= 0
        ):
            raise ProviderExecutionError(
                "Adapter não pode executar sem timeout de transporte válido "
                "resolvido pelo PedroCore."
            )
        return transport_timeout_ms

    def _normalize(
        self,
        response: object,
        *,
        model: str,
        budget: int,
        timeout_ms: int,
    ) -> ProviderResponse:
        finish_reason = _finish_reason_of(response)
        input_tokens, output_tokens, total_tokens = _usage_of(response)
        text = getattr(response, "text", "") or ""

        # O custo já foi incorrido nos caminhos abaixo: os metadados de uso
        # viajam com a exceção em vez de serem descartados.
        usage_kwargs = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "output_budget": budget,
            "transport_timeout_ms": timeout_ms,
        }

        if finish_reason == FINISH_REASON_MAX_TOKENS:
            # Truncamento é evidência explícita do provider, jamais inferido do
            # tamanho do texto. Nenhuma continuação, nenhum retry.
            raise ProviderOutputRejectedError(
                TRUNCATED_MESSAGE,
                finish_reason=finish_reason,
                truncated=True,
                **usage_kwargs,
            )

        if finish_reason is not None and finish_reason not in _NORMAL_FINISH_REASONS:
            # SAFETY, RECITATION, BLOCKLIST, PROHIBITED_CONTENT, SPII,
            # MALFORMED_FUNCTION_CALL, LANGUAGE, OTHER e demais: tratamento
            # conservador. A mensagem carrega só o rótulo, nunca o conteúdo.
            raise ProviderOutputRejectedError(
                f"{ABNORMAL_FINISH_MESSAGE} (finish_reason={finish_reason})",
                finish_reason=finish_reason,
                truncated=False,
                **usage_kwargs,
            )

        if not text.strip():
            raise ProviderExecutionError(EMPTY_TEXT_MESSAGE)

        return ProviderResponse(
            answer=text,
            provider=self.name,
            model=model,
            finish_reason=finish_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            truncated=False,
            output_budget=budget,
            transport_timeout_ms=timeout_ms,
        )

    @staticmethod
    async def _aclose(client: object) -> TransportClose:
        """Fecha o cliente e DEVOLVE o resultado observado.

        Falha de fechamento nunca substitui a exceção em curso nem transforma
        sucesso em erro — mas também nunca é registrada como fechamento
        concluído. Tentativa e confirmação são fatos distintos.
        """
        aio = getattr(client, "aio", None)
        aclose = getattr(aio, "aclose", None)
        if aclose is None:
            return TransportClose.NOT_ATTEMPTED
        try:
            await aclose()
        except Exception:
            return TransportClose.FAILED
        return TransportClose.CONFIRMED
