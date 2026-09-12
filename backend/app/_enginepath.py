"""
Motor yolu çözücü — `reloop.py` çekirdeğini bulur ve sys.path'e ekler.

Neden: dev düzeninde reloop.py `ReLoop_demo/` altında (backend'in üstünde);
Docker imajında ise `/srv/` altında (app'in kardeşi). Sabit `parent.parent.parent`
iki düzende farklı yer gösterir. Bu çözücü yukarı doğru arar + RELOOP_ENGINE_DIR
ortam değişkenini onurlandırır → her iki düzende de çalışır.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

_resolved: str | None = None


def ensure_engine_on_path() -> str:
    global _resolved
    if _resolved:
        return _resolved
    candidates: list[Path] = []
    env = os.environ.get("RELOOP_ENGINE_DIR")
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates.extend([here.parent, *here.parents])
    for c in candidates:
        if c and (c / "reloop.py").exists():
            if str(c) not in sys.path:
                sys.path.insert(0, str(c))
            _resolved = str(c)
            return _resolved
    raise RuntimeError("reloop.py motor çekirdeği bulunamadı (RELOOP_ENGINE_DIR ayarlayın)")
