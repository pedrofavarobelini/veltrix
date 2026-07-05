import os

import pytest

# Helper para testes opt-in de recursos reais (IMPLEMENT-05A).
# Um teste marcado com optin(FLAG) só roda quando a flag de ambiente
# correspondente estiver explicitamente "true". No pytest padrão, é SKIPPED.


def flag_is_true(env_name: str) -> bool:
    return (os.environ.get(env_name) or "").strip().lower() == "true"


def optin(env_name: str):
    return pytest.mark.skipif(
        not flag_is_true(env_name),
        reason=f"teste real opt-in; defina {env_name}=true para executar",
    )
