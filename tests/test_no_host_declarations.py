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


def test_bank_mini_is_one_line_with_imports():
    path = Path(__file__).resolve().parents[1] / "examples" / "bank.mini.py"
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    assert len(lines) == 1, "examples/bank.mini.py should be exactly one line"
    line = lines[0]
    assert line.startswith("import sys;"), line[:80]
    assert "from notmonad import" in line
    assert "app, reset_db, seed =" in line.replace(" ", "") or (
        "app,reset_db,seed=" in line.replace(" ", "")
    )
    tree = ast.parse(source, filename=str(path))
    assigns = [node for node in tree.body if isinstance(node, ast.Assign)]
    assert len(assigns) == 1
    assert [name.id for name in assigns[0].targets[0].elts] == [
        "app",
        "reset_db",
        "seed",
    ]
    for node in ast.walk(tree):
        assert not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ), "bank.mini.py must stay declaration-free"


def test_web_combinators_are_chain_pipelines():
    path = Path(__file__).resolve().parents[1] / "notmonad" / "web.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        assert not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ), "notmonad.web must be combinators (lambda), not def/class"
    assert "chain(" in source
    assert "Seq" in source


def test_imported_helpers_are_chain_lambdas():
    root = Path(__file__).resolve().parents[1]
    expected = {
        root / "notmonad" / "ops.py": [
            "identity",
            "const",
            "tap",
            "effect",
            "if_else",
            "when",
            "unless",
            "recover",
            "get",
            "inc",
        ],
        root / "notmonad" / "data.py": [
            "atom",
            "deref",
            "swap",
            "assoc",
            "assoc_in",
            "get_in",
            "dmerge",
        ],
        root / "notmonad" / "web.py": [
            "html_response",
            "redirect",
            "response",
            "router",
            "GET",
            "POST",
        ],
    }
    for path, names in expected.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id in names:
                    found[target.id] = node.value
        for name in names:
            assert name in found, f"{path.name} is missing {name}"
            assert isinstance(found[name], ast.Lambda), (
                f"{path.name}:{name} should be a lambda chain procedure, not def"
            )
        text = path.read_text(encoding="utf-8")
        assert "chain(" in text


def test_oneline_and_bank_do_not_import_web():
    root = Path(__file__).resolve().parents[1] / "examples"
    for name in ("oneline.py", "bank.py", "bank.mini.py"):
        source = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(root / name))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("notmonad.web"), (
                    f"{name} should inline HTTP helpers in the chain, "
                    "not import notmonad.web"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("notmonad.web")


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
