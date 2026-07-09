"""Executor local do Eval Harness determinístico.

Uso (a partir de apps/api):

    uv run python -m app.modules.eval_harness.run

Não chama provider real, não chama rede e não depende de modelo local.
"""

import json

from app.modules.eval_harness.service import eval_harness_service


def main() -> int:
    result = eval_harness_service.run_sync()
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
