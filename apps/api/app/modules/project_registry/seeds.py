"""Projetos iniciais — configuração, não regra.

Estes nomes são SEEDS: o catálogo começa com eles para que a primeira abertura
do console não mostre uma lista vazia. Eles não são especiais em lugar nenhum
do código.

O teste `test_the_core_never_branches_on_a_project_name` existe exatamente para
manter isso verdadeiro: se algum dia aparecer um `if project_id == "finguard"`
no núcleo, ele falha. Um projeto novo entra pelo registry e funciona igual —
inclusive um criado pelo usuário há dez segundos.

Nenhuma capacidade é concedida aqui. Um seed sem Capability Manifest fica
exatamente como qualquer projeto novo: os fatos que o manifesto traria ficam
`UNKNOWN`.
"""

from __future__ import annotations

# (id, nome de exibição). Nada além de identidade — sem caminho, sem
# repositório, sem capacidade.
SEED_PROJECTS: tuple[tuple[str, str], ...] = (
    # `pedrocore` e o identificador HISTORICO do proprio produto, preservado
    # pela mesma regra do rename: nome de exibicao muda, identidade nao.
    # Trocar a chave aqui orfanaria o Capability Manifest, a Project Surface e
    # todo o historico de analise ja gravado sob ela.
    ("pedrocore", "Veltrix"),
    ("finguard", "FinGuard"),
    ("structa", "Structa"),
    ("elyra", "Elyra"),
    ("rivvo", "RIVVO"),
    ("orlabyte", "OrlaByte"),
)
