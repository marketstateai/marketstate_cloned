import ast
import pathlib
import pytest

EXCLUDED_DIRS = {'venv', '.venv', '__pycache__', '.git', 'msvenv'}

def is_excluded(path: pathlib.Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)

def get_python_files():
    return [
        path for path in pathlib.Path(".").rglob("*.py")
        if not is_excluded(path)
    ]

def is_hardcoded_password_assign(node: ast.Assign) -> bool:
    for target in node.targets:
        if isinstance(target, ast.Name) and target.id.lower() == "password":
            # Check if the value is a hardcoded constant
            return isinstance(node.value, (ast.Constant, ast.Str, ast.Num))
    return False

def test_no_hardcoded_passwords():
    flagged = []

    for file in get_python_files():
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and is_hardcoded_password_assign(node):
                lineno = node.lineno
                line = file.read_text(encoding="utf-8").splitlines()[lineno - 1].strip()
                flagged.append(f"{file}:{lineno}: {line}")
    
    if flagged:
        pytest.fail("❌ Hardcoded passwords found:\n" + "\n".join(flagged))
