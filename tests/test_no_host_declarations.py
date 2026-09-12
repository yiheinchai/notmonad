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


def test_oneline_is_one_assignment_without_def_or_class():
    path = Path(__file__).resolve().parents[1] / "examples" / "oneline.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    assigns = [node for node in tree.body if isinstance(node, ast.Assign)]
    assert len(assigns) == 1, "examples/oneline.py should be one assignment"
    assert [name.id for name in assigns[0].targets[0].elts] == [
        "app",
        "reset_db",
        "seed",
    ]
    for node in ast.walk(tree):
        assert not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ), "oneline demo must inline everything — no def or class"


def test_bank_is_one_assignment_without_def_or_class():
    path = Path(__file__).resolve().parents[1] / "examples" / "bank.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    assigns = [node for node in tree.body if isinstance(node, ast.Assign)]
    assert len(assigns) == 1, "examples/bank.py should be one assignment"
    assert [name.id for name in assigns[0].targets[0].elts] == [
        "app",
        "reset_db",
        "seed",
    ]
    for node in ast.walk(tree):
        assert not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ), "bank demo must inline everything — no def or class"


def test_site_app_modules_are_chain_pipelines():
    skip = {"templates.py", "__init__.py"}
    files = [path for path in SITE.glob("*.py") if path.name not in skip]
    assert files, "examples/site is missing"
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "chain(" in text, (
            f"{path.name} should be a chain(..., App) pipeline, "
            "not let/cond/do control flow"
        )
