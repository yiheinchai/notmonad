"""Application modules must stay declaration-free Python (no def/class)."""

import ast
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "examples" / "site"


def test_site_is_python_without_def_or_class():
    files = list(SITE.glob("*.py"))
    assert files, "examples/site is missing"
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            assert not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ), f"{path.name} contains {type(node).__name__} — app code must use notmonad combinators, not def/class"
