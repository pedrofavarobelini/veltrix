"""Rotas de plataforma: Control Center, compatibilidade e saude.

Todas somente-leitura, e todas atras da mesma autorizacao tecnica que o resto
das APIs operacionais ja usa. Nao ha aqui nenhuma rota que mute estado: as
decisoes que mudam alguma coisa continuam nas rotas que ja respondem por elas,
com a autorizacao que ja tinham.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.modules.caller_identity.schemas import SHARED_OR_UNKNOWN_PROJECT_ID
from app.modules.caller_identity.service import caller_identity_service
from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    read_api_key,
)
from app.modules.compatibility.schemas import CompatibilityAnswer, CompatibilityQuery
from app.modules.compatibility.service import compatibility_service
from app.modules.control_center.service import (
    ControlCenterSnapshot,
    control_center_service,
)
from app.modules.slo.service import HealthSnapshot, slo_service

router = APIRouter(tags=["Platform Control Plane"])


def _authorize_server_scope(request: Request):
    """Autoriza uma leitura sobre o SERVIDOR, e nao sobre um projeto.

    Control Center e SLO nao expoem dado de consumidor algum — so contagens e
    estados. Mas exigir o namespace compartilhado recusaria justamente quem
    tem credencial de projeto registrada, que e quem legitimamente opera.

    Entao o projeto autorizado passa a ser o PROPRIO projeto do chamador,
    resolvido da credencial. A autorizacao continua sendo a mesma de sempre:
    quem nao se autentica nao passa, e a decisao segue fail-closed.
    """
    resolucao = caller_identity_service.resolve(read_api_key(request))
    escopo = SHARED_OR_UNKNOWN_PROJECT_ID
    if resolucao.context is not None and resolucao.context.project_id:
        escopo = resolucao.context.project_id
    return authorize_technical_request(request, escopo)


@router.get("/control-center/snapshot", response_model=ControlCenterSnapshot)
def control_center_snapshot(request: Request):
    """Retrato operacional agregado. Somente leitura."""
    error, _warnings, caller = _authorize_server_scope(request)
    if error is not None:
        return error
    assert caller is not None
    return control_center_service.snapshot()


@router.get("/health/slo", response_model=HealthSnapshot)
def slo_snapshot(request: Request):
    """Estado dos indicadores. Sem medicao, o indicador sai UNKNOWN."""
    error, _warnings, caller = _authorize_server_scope(request)
    if error is not None:
        return error
    assert caller is not None
    return slo_service.snapshot()


@router.post("/compatibility/check", response_model=CompatibilityAnswer)
def compatibility_check(payload: CompatibilityQuery, request: Request):
    """Responde 'este consumidor pode usar isto com estas versões?'.

    A pergunta e feita sobre o projeto declarado no payload, e a credencial
    precisa corresponder a ele — perguntar pela compatibilidade de outro
    projeto revelaria o que ele declara.
    """
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    return compatibility_service.check(payload)
