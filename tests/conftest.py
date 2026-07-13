import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_PYTHON_DIR = _RAIZ / "python"
for _dir in (_PYTHON_DIR, _RAIZ):
    # `_RAIZ` é necessário pra `scraping/` (vive na raiz do repo, fora de
    # `python/`, e não é pacote instalável) -- sem isso, `pytest` funciona
    # só quando invocado via `python -m pytest` (o `-m` insere o CWD no
    # sys.path como efeito colateral); `pytest` puro (ex.: CI) não insere,
    # e `import scraping...` falha com ModuleNotFoundError.
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))
