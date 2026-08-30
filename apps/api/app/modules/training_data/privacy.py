"""Scanner de privacidade do Learning Plane.

Os padroes vivem em `universal_contracts/privacy_patterns.py` (Shared Kernel)
desde a Era 4, porque a Evidence Platform precisa da mesma protecao na porta de
entrada e duas copias da mesma lista divergiriam na primeira vez que alguem
acrescentasse um padrao em um lado so.

Este modulo continua sendo a API do Learning Plane: ele mapeia os achados para
`PrivacyFinding`, que e o tipo que a politica de elegibilidade consome. A
assinatura e o comportamento de `scan_payload` nao mudaram.
"""

from __future__ import annotations

from pydantic import JsonValue

from app.modules.training_data.schemas import PrivacyFinding
from app.modules.universal_contracts.privacy_patterns import detect


def scan_payload(sections: dict[str, JsonValue]) -> list[PrivacyFinding]:
    """Achados de privacidade no payload do candidato.

    O caminho reportado comeca em `candidate` por compatibilidade: codigos de
    rejeicao e evidencias ja gravadas referenciam esse prefixo.
    """
    return [
        PrivacyFinding(code=code, category=category, field_path=field_path)
        for code, category, field_path in detect(sections, root="candidate")
    ]
