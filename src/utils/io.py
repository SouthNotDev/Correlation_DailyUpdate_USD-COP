"""Helpers para manejo de directorios usados en el pipeline diario.

Briefing rápido:
- `ensure_dir(path)` crea (si hace falta) y devuelve el directorio indicado.
- `date_folder(base_dir, subdir, date_str)` crea una carpeta del tipo
  `base_dir/raw/<subdir>/<fecha>` y la devuelve como `Path`.

Estas funciones se utilizan en distintos módulos para centralizar la lógica
de creación de carpetas antes de escribir archivos de datos o reportes.
"""

from __future__ import annotations

import os
from pathlib import Path


def ensure_dir(path: str | os.PathLike) -> Path:
    """Garantiza que exista el directorio indicado y retorna la ruta como `Path`."""

    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def date_folder(base_dir: str | os.PathLike, subdir: str, date_str: str) -> Path:
    """Crea la carpeta diaria dentro de `base_dir/raw/<subdir>/<fecha>` y la devuelve."""

    p = Path(base_dir) / "raw" / subdir / date_str
    p.mkdir(parents=True, exist_ok=True)
    return p
