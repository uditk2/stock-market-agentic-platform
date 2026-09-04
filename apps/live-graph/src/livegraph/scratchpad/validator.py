"""Static gate on generated code.

Since strategies execute inside a locked-down container, this is a linter for
fast feedback, not a security boundary. It catches the two failure modes worth
catching before paying for a container start: the code does not parse, or it
does not define the entrypoint the runner will call.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .contract import BLOCKED_IMPORTS, ENTRYPOINT


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    reasons: tuple[str, ...] = ()

    @property
    def message(self) -> str:
        return "; ".join(self.reasons)


def validate(code: str) -> ValidationResult:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return ValidationResult(False, (f"syntax error: {exc.msg} (line {exc.lineno})",))

    reasons = (*_check_entrypoint(tree), *_check_blocked_imports(tree))
    return ValidationResult(not reasons, reasons)


def _check_entrypoint(tree: ast.Module) -> tuple[str, ...]:
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == ENTRYPOINT
    ]
    if functions and isinstance(functions[0], ast.AsyncFunctionDef):
        return (f"`{ENTRYPOINT}` must be a plain function, not async",)
    if not functions:
        return (f"no top-level `def {ENTRYPOINT}(ctx)` found",)
    if len(functions[0].args.args) != 1:
        return (f"`{ENTRYPOINT}` must take exactly one argument (ctx)",)
    return ()


def _check_blocked_imports(tree: ast.Module) -> tuple[str, ...]:
    blocked = {
        name
        for node in ast.walk(tree)
        for name in _imported_roots(node)
        if name in BLOCKED_IMPORTS
    }
    return tuple(f"import of '{name}' is not allowed" for name in sorted(blocked))


def _imported_roots(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name.split(".")[0] for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [(node.module or "").split(".")[0]]
    return []
