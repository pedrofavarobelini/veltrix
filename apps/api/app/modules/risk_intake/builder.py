"""Auto Context Builder: resolve o contexto a partir do que já existe.

O problema que ele resolve
--------------------------

Onze campos avançados para preencher a cada análise torna a ferramenta
inviável no uso diário. Mas preenchê-los sozinho, sem dizer de onde veio cada
valor, foi exatamente o defeito que a homologação encontrou nos placeholders.

A saída é uma PROPOSTA, com origem e confiança por campo, para um humano
confirmar. Nada é submetido sem passar por ele.

O princípio que governa a permissão
-----------------------------------

    capacidade pedida  !=  permissão concedida

    pedida  ∩  executor  ∩  projeto  ∩  política  =  efetiva

Qualquer camada que negue produz `FORBIDDEN`. Faltando base para decidir,
`UNKNOWN` — que nunca é tratado como permitido.

Determinístico por inteiro
--------------------------

Não há IA neste caminho. A inferência é casamento de vocabulário DECLARADO
sobre o texto já segmentado por polaridade — o mesmo módulo que corrigiu o bug
de negação, reutilizado, sem parser paralelo.

Se um AI Mapper for acrescentado depois, ele só poderá PROPOR: a validação
determinística continua sendo a autoridade, e a ausência do provider mantém
este caminho funcionando inteiro.
"""

from __future__ import annotations

from app.modules.policy_engine.schemas import (
    PolicyDecision,
    PolicyDomain,
    PolicyRequest,
)
from app.modules.policy_engine.service import policy_engine_service
from app.modules.risk_engine.polarity import (
    affirmative_text,
    forbidden_text,
)
from app.modules.risk_engine.schemas import OperationKind
from app.modules.risk_intake.capabilities import (
    CAPABILITY_TERMS,
    TechnicalCapability,
    area_slug,
    executor_profile,
    project_surface,
)
from app.modules.risk_intake.schemas import (
    Confidence,
    ContextOrigin,
    ContextProposal,
    EffectivePermission,
    PermissionDecision,
    ProposedField,
)

# --- codigos de motivo ----------------------------------------------------

NOT_REQUESTED = "NOT_REQUESTED"
FORBIDDEN_BY_PROMPT = "FORBIDDEN_BY_PROMPT"
EXECUTOR_LACKS_CAPABILITY = "EXECUTOR_LACKS_CAPABILITY"
PROJECT_LACKS_SURFACE = "PROJECT_LACKS_SURFACE"
POLICY_DENIED = "POLICY_DENIED"
EXECUTOR_UNKNOWN = "EXECUTOR_UNKNOWN"
PROJECT_UNKNOWN = "PROJECT_UNKNOWN"
INTERSECTION_SATISFIED = "INTERSECTION_SATISFIED"

# Capacidades que mudam estado. Uma proposta que as inclua sem o humano ter
# declarado precisa de revisão antes de virar requisição.
_MUTATING = frozenset(
    {
        TechnicalCapability.FILESYSTEM_WRITE,
        TechnicalCapability.GIT_COMMIT,
        TechnicalCapability.GIT_PUSH,
        TechnicalCapability.DATABASE,
        TechnicalCapability.MIGRATION,
        TechnicalCapability.DEPLOYMENT,
        TechnicalCapability.CONTAINERS,
    }
)

# Da capacidade tecnica para a operacao do contrato V1. Ordem do mais grave.
_CAPABILITY_TO_OPERATION: tuple[tuple[TechnicalCapability, OperationKind], ...] = (
    (TechnicalCapability.MIGRATION, OperationKind.MIGRATE),
    (TechnicalCapability.DEPLOYMENT, OperationKind.DEPLOY),
    (TechnicalCapability.DATABASE, OperationKind.MIGRATE),
    (TechnicalCapability.FILESYSTEM_WRITE, OperationKind.WRITE),
    (TechnicalCapability.GIT_PUSH, OperationKind.EXECUTE),
    (TechnicalCapability.GIT_COMMIT, OperationKind.EXECUTE),
    (TechnicalCapability.TERMINAL, OperationKind.EXECUTE),
    (TechnicalCapability.TESTS, OperationKind.EXECUTE),
    (TechnicalCapability.FILESYSTEM_READ, OperationKind.READ),
)


def _mentions(text: str, terms: tuple[str, ...]) -> bool:
    baixo = text.lower()
    return any(termo in baixo for termo in terms)


def _verb_positions(text: str) -> list[tuple[int, bool]]:
    """Posicoes dos verbos, com a marca de mutacao.

    `True` = o verbo MUDA estado. `False` = o verbo verifica ou le.
    """
    posicoes: list[tuple[int, bool]] = []
    for capacidade, termos in CAPABILITY_TERMS.items():
        muda = capacidade in _MUTATING
        for termo in termos:
            inicio = text.find(termo)
            while inicio != -1:
                posicoes.append((inicio, muda))
                inicio = text.find(termo, inicio + 1)
    return sorted(posicoes)


def _classify_areas(text: str, areas: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Separa areas citadas em ALVO DE MUTACAO e ALVO DE VERIFICACAO.

    A distincao importa porque escopo de mutacao e AUTORIZACAO: incluir
    `module:testes` so porque os testes serao executados ampliaria o que pode
    ser alterado, sem ninguem ter pedido.

    Como a decisao e tomada
    -----------------------

    Pelo verbo mais PROXIMO que precede a area, e nao pela oracao inteira.

        "Atualize apenas o Risk Console, rode os testes relacionados"
                ^mutacao         ^area          ^verificacao  ^area

    Uma virgula nao separa oracoes aqui — a frase e uma so — mas os dois
    verbos governam trechos diferentes dela. Classificar a oracao inteira
    tornaria `testes` alvo de alteracao por vizinhanca.

    Nao e analise sintatica: e proximidade. Resolve o caso que aparece em
    prompt de instrucao e falha para o lado seguro, porque area sem verbo de
    mutacao antes dela nunca vira alvo de mutacao.
    """
    from app.modules.risk_engine.polarity import split_clauses

    mutacao: list[str] = []
    verificacao: list[str] = []
    ordenadas = sorted(areas, key=len, reverse=True)
    vistas: set[str] = set()

    for clausula in split_clauses(text):
        if not clausula.affirmative:
            continue
        baixo = clausula.text.lower()
        verbos = _verb_positions(baixo)

        for area in ordenadas:
            posicao = baixo.find(area)
            if posicao == -1:
                continue
            slug = area_slug(area)
            if slug in vistas:
                continue
            vistas.add(slug)

            anteriores = [muda for indice, muda in verbos if indice < posicao]
            # Sem verbo antes da area, ela nao e alvo de alteracao. Assumir
            # mutacao por omissao seria ampliar escopo por omissao.
            destino = mutacao if anteriores and anteriores[-1] else verificacao
            destino.append(slug)
    return mutacao, verificacao


class AutoContextBuilder:
    """Constrói a proposta. Não autoriza, não analisa, não decide gate."""

    def build(
        self,
        *,
        prompt: str,
        project_id: str,
        environment: str,
        executor: str,
        declared: dict[str, tuple[str, ...]] | None = None,
    ) -> ContextProposal:
        """Resolve o contexto a partir do prompt e do que já está declarado.

        `declared` são os campos que o humano já preencheu à mão. Eles têm
        precedência absoluta: o builder propõe onde falta, e nunca por cima.
        """
        declarado = {k: tuple(v) for k, v in (declared or {}).items() if v}
        afirmativo = affirmative_text(prompt)
        proibido = forbidden_text(prompt)

        permissoes = self._permissions(
            afirmativo=afirmativo,
            proibido=proibido,
            project_id=project_id,
            environment=environment,
            executor=executor,
        )
        campos = self._fields(
            prompt=prompt,
            afirmativo=afirmativo,
            project_id=project_id,
            declarado=declarado,
            permissoes=permissoes,
        )
        return ContextProposal(
            project_id=project_id.strip().lower(),
            environment=environment,
            executor=executor,
            fields=campos,
            permissions=permissoes,
        )

    # --- permissoes -------------------------------------------------------

    def _permissions(
        self,
        *,
        afirmativo: str,
        proibido: str,
        project_id: str,
        environment: str,
        executor: str,
    ) -> list[PermissionDecision]:
        perfil = executor_profile(executor)
        superficie = project_surface(project_id)

        decisoes: list[PermissionDecision] = []
        for capacidade, termos in CAPABILITY_TERMS.items():
            pedida = _mentions(afirmativo, termos)
            vetada = _mentions(proibido, termos) and not pedida

            executor_ok = perfil.supports(capacidade) if perfil else False
            projeto_ok = superficie.has(capacidade) if superficie else False
            politica_ok, politica_motivos = self._policy_allows(
                capacidade=capacidade,
                project_id=project_id,
                environment=environment,
                executor=executor,
                requested=pedida,
            )

            efetiva, motivos, explicacao = self._intersect(
                capacidade=capacidade,
                pedida=pedida,
                vetada=vetada,
                executor_ok=executor_ok,
                projeto_ok=projeto_ok,
                politica_ok=politica_ok,
                perfil_existe=perfil is not None,
                superficie_existe=superficie is not None,
            )
            decisoes.append(
                PermissionDecision(
                    capability=capacidade,
                    requested=pedida,
                    forbidden_by_prompt=vetada,
                    executor_supports=executor_ok,
                    project_has=projeto_ok,
                    policy_allows=politica_ok,
                    effective=efetiva,
                    reason_codes=tuple(motivos) + tuple(politica_motivos),
                    explanation=explicacao,
                )
            )
        return decisoes

    @staticmethod
    def _intersect(
        *,
        capacidade: TechnicalCapability,
        pedida: bool,
        vetada: bool,
        executor_ok: bool,
        projeto_ok: bool,
        politica_ok: bool,
        perfil_existe: bool,
        superficie_existe: bool,
    ) -> tuple[EffectivePermission, list[str], str]:
        """A interseção, na ordem que importa.

        A proibição do prompt vem primeiro: o humano dizendo "não faça push" é
        o sinal mais forte que existe, e nenhuma camada posterior o reverte.
        """
        if vetada:
            return (
                EffectivePermission.FORBIDDEN,
                [FORBIDDEN_BY_PROMPT],
                "Proibido explicitamente no prompt.",
            )
        if not pedida:
            return (
                EffectivePermission.UNKNOWN,
                [NOT_REQUESTED],
                "Não solicitado pelo prompt.",
            )
        if not perfil_existe:
            return (
                EffectivePermission.UNKNOWN,
                [EXECUTOR_UNKNOWN],
                "Executor sem perfil declarado; capacidade não pôde ser verificada.",
            )
        if not executor_ok:
            return (
                EffectivePermission.FORBIDDEN,
                [EXECUTOR_LACKS_CAPABILITY],
                f"O executor não possui a capacidade {capacidade.value}.",
            )
        if not superficie_existe:
            return (
                EffectivePermission.UNKNOWN,
                [PROJECT_UNKNOWN],
                "Projeto sem superfície declarada; não foi possível verificar.",
            )
        if not projeto_ok:
            return (
                EffectivePermission.FORBIDDEN,
                [PROJECT_LACKS_SURFACE],
                f"O projeto não declara superfície para {capacidade.value}.",
            )
        if not politica_ok:
            return (
                EffectivePermission.FORBIDDEN,
                [POLICY_DENIED],
                "Negado pela política aplicável.",
            )
        return (
            EffectivePermission.GRANTED,
            [INTERSECTION_SATISFIED],
            "Pedido, suportado pelo executor, existente no projeto e permitido.",
        )

    @staticmethod
    def _policy_allows(
        *,
        capacidade: TechnicalCapability,
        project_id: str,
        environment: str,
        executor: str,
        requested: bool,
    ) -> tuple[bool, list[str]]:
        """Consulta o Policy Engine existente, sem regra paralela."""
        if not requested:
            return True, []
        avaliacao = policy_engine_service.evaluate(
            PolicyRequest(
                domain=PolicyDomain.EXECUTION,
                action=capacidade.value,
                project_id=project_id,
                environment=environment,
                producer=f"risk-intake:{executor}",
                attributes={"mutating": capacidade in _MUTATING},
            )
        )
        if avaliacao.decision is PolicyDecision.DENY:
            return False, list(avaliacao.reason_codes)
        # REVIEW_REQUIRED nao nega, mas tambem nao libera em silencio: o motivo
        # viaja para a tela de revisao.
        return True, list(avaliacao.reason_codes)

    # --- campos -----------------------------------------------------------

    def _fields(
        self,
        *,
        prompt: str,
        afirmativo: str,
        project_id: str,
        declarado: dict[str, tuple[str, ...]],
        permissoes: list[PermissionDecision],
    ) -> list[ProposedField]:
        campos: list[ProposedField] = []
        por_capacidade = {item.capability: item for item in permissoes}

        campos.append(self._operation(afirmativo, declarado, por_capacidade))
        campos.append(self._targets(afirmativo, project_id, declarado))
        campos.append(self._allowed_scope(campos[-1], declarado))
        campos.append(self._forbidden_scope(permissoes, declarado))
        campos.append(self._requested_permissions(permissoes, declarado))
        campos.append(self._effective_permissions(permissoes))
        superficie = project_surface(project_id)
        _mutacao, verificacao = (
            _classify_areas(afirmativo, superficie.areas) if superficie else ([], [])
        )
        campos.append(
            self._required_tests(por_capacidade, declarado, tuple(verificacao))
        )
        campos.append(self._database(por_capacidade, declarado))
        campos.append(self._rollback(por_capacidade, declarado))
        return campos

    @staticmethod
    def _declared(
        declarado: dict[str, tuple[str, ...]], nome: str, rotulo: str
    ) -> ProposedField | None:
        valores = declarado.get(nome)
        if not valores:
            return None
        return ProposedField(
            field=nome,
            label=rotulo,
            values=valores,
            origin=ContextOrigin.DECLARED,
            confidence=Confidence.HIGH,
            reason="Declarado por você nas Configurações Avançadas.",
        )

    def _operation(self, afirmativo, declarado, por_capacidade) -> ProposedField:
        ja = self._declared(declarado, "operation", "Operação")
        if ja:
            return ja
        for capacidade, operacao in _CAPABILITY_TO_OPERATION:
            decisao = por_capacidade.get(capacidade)
            if decisao and decisao.requested:
                return ProposedField(
                    field="operation",
                    label="Operação",
                    values=(operacao.value,),
                    origin=ContextOrigin.INFERRED,
                    confidence=Confidence.HIGH,
                    reason=f"O prompt pede {capacidade.value}.",
                    confirmation_required=capacidade in _MUTATING,
                )
        return ProposedField(
            field="operation",
            label="Operação",
            values=(),
            origin=ContextOrigin.UNKNOWN,
            confidence=Confidence.LOW,
            reason="Nenhuma operação identificável no que o prompt pede.",
            confirmation_required=True,
        )

    def _targets(self, afirmativo, project_id, declarado) -> ProposedField:
        ja = self._declared(declarado, "targets", "Alvos")
        if ja:
            return ja
        superficie = project_surface(project_id)
        if superficie is None:
            return ProposedField(
                field="targets",
                label="Alvos",
                values=(),
                origin=ContextOrigin.UNKNOWN,
                confidence=Confidence.LOW,
                reason="Projeto sem áreas declaradas; alvo não pôde ser inferido.",
                confirmation_required=True,
            )
        encontradas, _verificacao = _classify_areas(afirmativo, superficie.areas)
        if not encontradas:
            return ProposedField(
                field="targets",
                label="Alvos",
                values=(),
                origin=ContextOrigin.UNKNOWN,
                confidence=Confidence.LOW,
                # Nao virar "o projeto inteiro" e a decisao central aqui: um
                # alvo amplo inventado seria autorizacao ampla inventada.
                reason="Nenhuma área do projeto foi citada como alvo de alteração.",
                confirmation_required=True,
            )
        return ProposedField(
            field="targets",
            label="Alvos",
            values=tuple(dict.fromkeys(encontradas)),
            origin=ContextOrigin.INFERRED,
            confidence=Confidence.HIGH if len(encontradas) == 1 else Confidence.MEDIUM,
            reason="Áreas que o prompt pede para ALTERAR.",
            confirmation_required=True,
        )

    def _allowed_scope(self, alvos: ProposedField, declarado) -> ProposedField:
        ja = self._declared(declarado, "allowed_scope", "Escopo permitido")
        if ja:
            return ja
        if not alvos.values:
            return ProposedField(
                field="allowed_scope",
                label="Escopo permitido",
                values=(),
                origin=ContextOrigin.UNKNOWN,
                confidence=Confidence.LOW,
                reason="Sem alvo identificado, não há escopo a propor.",
                confirmation_required=True,
            )
        return ProposedField(
            field="allowed_scope",
            label="Escopo permitido",
            values=tuple(f"module:{item}" for item in alvos.values),
            origin=ContextOrigin.INFERRED,
            confidence=alvos.confidence,
            reason="Derivado dos alvos identificados; nada além deles.",
            confirmation_required=True,
        )

    def _forbidden_scope(self, permissoes, declarado) -> ProposedField:
        ja = self._declared(declarado, "forbidden_scope", "Escopo proibido")
        vetadas = tuple(
            item.capability.value for item in permissoes if item.forbidden_by_prompt
        )
        if ja and not vetadas:
            return ja
        valores = tuple(dict.fromkeys((ja.values if ja else ()) + vetadas))
        if not valores:
            return ProposedField(
                field="forbidden_scope",
                label="Escopo proibido",
                values=(),
                origin=ContextOrigin.UNKNOWN,
                confidence=Confidence.LOW,
                reason="Nada foi proibido explicitamente.",
            )
        return ProposedField(
            field="forbidden_scope",
            label="Escopo proibido",
            values=valores,
            origin=ContextOrigin.DECLARED if ja else ContextOrigin.INFERRED,
            confidence=Confidence.HIGH,
            # Proibicao vinda do prompt e declaracao do humano, ainda que em
            # prosa: ele escreveu "nao faca push".
            reason="Proibido explicitamente no prompt.",
        )

    def _requested_permissions(self, permissoes, declarado) -> ProposedField:
        ja = self._declared(declarado, "requested_permissions", "Permissões pedidas")
        if ja:
            return ja
        pedidas = tuple(item.capability.value for item in permissoes if item.requested)
        if not pedidas:
            return ProposedField(
                field="requested_permissions",
                label="Permissões pedidas",
                values=(),
                origin=ContextOrigin.UNKNOWN,
                confidence=Confidence.LOW,
                reason="O prompt não pede nenhuma capacidade reconhecida.",
                confirmation_required=True,
            )
        return ProposedField(
            field="requested_permissions",
            label="Permissões pedidas",
            values=pedidas,
            origin=ContextOrigin.INFERRED,
            confidence=Confidence.HIGH,
            reason="Capacidades que o prompt pede — pedir não é receber.",
            confirmation_required=True,
        )

    @staticmethod
    def _effective_permissions(permissoes) -> ProposedField:
        concedidas = tuple(
            item.capability.value
            for item in permissoes
            if item.effective is EffectivePermission.GRANTED
        )
        return ProposedField(
            field="effective_permissions",
            label="Permissões efetivas",
            values=concedidas,
            # POLICY_DERIVED e nao INFERRED: a interseccao e decisao de
            # politica, e apresenta-la como inferencia esconderia quem decidiu.
            origin=ContextOrigin.POLICY_DERIVED,
            confidence=Confidence.HIGH,
            reason="Interseção de pedido, executor, projeto e política.",
        )

    def _required_tests(
        self, por_capacidade, declarado, verificacao: tuple[str, ...] = ()
    ) -> ProposedField:
        ja = self._declared(declarado, "required_tests", "Testes exigidos")
        if ja:
            return ja
        decisao = por_capacidade.get(TechnicalCapability.TESTS)
        if decisao and decisao.requested:
            return ProposedField(
                field="required_tests",
                label="Testes exigidos",
                # Alvo de VERIFICACAO, e nao de mutacao. Executar um teste nao
                # autoriza altera-lo.
                values=verificacao or ("suíte relacionada ao pedido",),
                origin=ContextOrigin.INFERRED,
                confidence=Confidence.MEDIUM,
                reason="O prompt pede execução de testes — verificação, não alteração.",
            )
        return ProposedField(
            field="required_tests",
            label="Testes exigidos",
            values=(),
            origin=ContextOrigin.UNKNOWN,
            confidence=Confidence.LOW,
            reason="O prompt não menciona testes.",
        )

    def _database(self, por_capacidade, declarado) -> ProposedField:
        ja = self._declared(declarado, "database", "Banco de dados")
        if ja:
            return ja
        banco = por_capacidade.get(TechnicalCapability.DATABASE)
        migracao = por_capacidade.get(TechnicalCapability.MIGRATION)
        envolvido = (banco and banco.requested) or (migracao and migracao.requested)
        if envolvido:
            return ProposedField(
                field="database",
                label="Banco de dados",
                values=("declarado no pedido",),
                origin=ContextOrigin.INFERRED,
                confidence=Confidence.MEDIUM,
                reason="O prompt envolve banco de dados ou migração.",
                confirmation_required=True,
            )
        return ProposedField(
            field="database",
            label="Banco de dados",
            values=(),
            origin=ContextOrigin.UNKNOWN,
            confidence=Confidence.HIGH,
            # Confianca ALTA na AUSENCIA: a polaridade ja garantiu que uma
            # mencao proibida nao conta como pedido.
            reason="O pedido não envolve banco de dados.",
        )

    @staticmethod
    def _rollback(por_capacidade, declarado) -> ProposedField:
        migracao = por_capacidade.get(TechnicalCapability.MIGRATION)
        destrutivo = any(
            por_capacidade.get(item) and por_capacidade[item].requested
            for item in (
                TechnicalCapability.MIGRATION,
                TechnicalCapability.DEPLOYMENT,
                TechnicalCapability.DATABASE,
            )
        )
        if destrutivo or (migracao and migracao.requested):
            return ProposedField(
                field="rollback_requirement",
                label="Plano de rollback",
                values=("required",),
                origin=ContextOrigin.POLICY_DERIVED,
                confidence=Confidence.HIGH,
                reason="Operação sobre banco ou publicação exige plano de rollback.",
                confirmation_required=True,
            )
        return ProposedField(
            field="rollback_requirement",
            label="Plano de rollback",
            values=("recommended",),
            origin=ContextOrigin.POLICY_DERIVED,
            confidence=Confidence.MEDIUM,
            reason="Recomendado por padrão para operação que altera estado.",
        )


auto_context_builder = AutoContextBuilder()
