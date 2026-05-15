from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import ast

try:
    from . import _vext  # type: ignore[attr-defined]
except Exception:
    _vext = None


PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parents[0]
V_SOURCE_DIR = ROOT
V_CLI_SOURCE_DIR = ROOT / "cmd" / "pyast_parser"
PACKAGED_V_SOURCE_DIR = PKG_DIR / "_vsrc"
PARSER_BINARY = PKG_DIR / "_bin" / ("pyast_parser.exe" if os.name == "nt" else "pyast_parser")


def parse_expression(source: str) -> ast.Expression:
    payload = _run_parser("--json-expr", source)
    return ast.Expression(body=_expr_from_json(payload))


def parse_module(source: str) -> ast.Module:
    payload = _run_parser("--json", source)
    if payload.get("type") != "Module":
        raise ValueError(f"expected Module payload, got {payload.get('type')}")
    return ast.Module(body=[_stmt_from_json(item) for item in payload["body"]], type_ignores=[])


def _run_parser(mode: str, source: str) -> dict[str, Any]:
    if _vext is not None:
        payload = _vext.parse_json(mode, source, str(PKG_DIR))
        return json.loads(payload)

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        path = Path(handle.name)
        handle.write(source)

    cmd, cwd, module_path = _parser_command(mode, path)
    try:
        env = os.environ.copy()
        if module_path is not None:
            env["VMODULES"] = str(module_path)
        proc = subprocess.run(cmd, cwd=cwd, env=env, check=False, text=True, capture_output=True)
    finally:
        path.unlink(missing_ok=True)
        if module_path is not None:
            link = module_path / "pyast"
            link.unlink(missing_ok=True)
            shutil.rmtree(module_path, ignore_errors=True)

    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "unknown parser failure"
        raise ValueError(message)

    return json.loads(proc.stdout)


def _parser_command(mode: str, source_path: Path) -> tuple[list[str], Path, Path | None]:
    if PARSER_BINARY.exists():
        return [str(PARSER_BINARY), mode, str(source_path)], ROOT, None
    if PACKAGED_V_SOURCE_DIR.exists():
        module_path = _module_path_for(PACKAGED_V_SOURCE_DIR)
        packaged_cli = module_path / "pyast" / "cmd" / "pyast_parser"
        return ["v", "-enable-globals", "run", str(packaged_cli), mode, str(source_path)], ROOT, module_path
    module_path = _module_path_for(V_SOURCE_DIR)
    local_cli = module_path / "pyast" / "cmd" / "pyast_parser"
    return ["v", "-enable-globals", "run", str(local_cli), mode, str(source_path)], ROOT, module_path


def _module_path_for(source_dir: Path) -> Path:
    module_path = Path(tempfile.mkdtemp(prefix="pyast_vmodules_"))
    (module_path / "pyast").symlink_to(source_dir, target_is_directory=True)
    return module_path


def _stmt_from_json(data: dict[str, Any]) -> ast.stmt:
    kind = data["type"]
    if kind == "Import":
        return ast.Import(names=[ast.alias(name=item["name"], asname=None) for item in data["names"]])
    if kind == "Expr":
        return ast.Expr(value=_expr_from_json(data["value"]))
    if kind == "Assign":
        return ast.Assign(
            targets=[ast.Name(id=data["target"], ctx=ast.Store())],
            value=_expr_from_json(data["value"]),
            type_comment=None,
        )
    if kind == "Pass":
        return ast.Pass()
    if kind == "Break":
        return ast.Break()
    if kind == "Continue":
        return ast.Continue()
    if kind == "Return":
        raw = data["value"]
        return ast.Return(value=None if raw is None else _expr_from_json(raw))
    if kind == "If":
        return ast.If(
            test=_expr_from_json(data["test"]),
            body=[_stmt_from_json(item) for item in data["body"]],
            orelse=[_stmt_from_json(item) for item in data["orelse"]],
        )
    if kind == "While":
        return ast.While(
            test=_expr_from_json(data["test"]),
            body=[_stmt_from_json(item) for item in data["body"]],
            orelse=[_stmt_from_json(item) for item in data["orelse"]],
        )
    if kind == "For":
        return ast.For(
            target=ast.Name(id=data["target"], ctx=ast.Store()),
            iter=_expr_from_json(data["iter"]),
            body=[_stmt_from_json(item) for item in data["body"]],
            orelse=[_stmt_from_json(item) for item in data["orelse"]],
            type_comment=None,
        )
    if kind == "FunctionDef":
        node = ast.FunctionDef(
            name=data["name"],
            args=_arguments_from_names(data["args"]),
            body=[_stmt_from_json(item) for item in data["body"]],
            decorator_list=[],
            returns=None,
            type_comment=None,
        )
        _set_optional_field(node, "type_params", [])
        return node
    if kind == "ClassDef":
        node = ast.ClassDef(
            name=data["name"],
            bases=[_expr_from_json(item) for item in data["bases"]],
            keywords=[],
            body=[_stmt_from_json(item) for item in data["body"]],
            decorator_list=[],
        )
        _set_optional_field(node, "type_params", [])
        return node
    raise ValueError(f"unsupported statement type: {kind}")


def _expr_from_json(data: dict[str, Any]) -> ast.expr:
    kind = data["type"]
    if kind == "Constant":
        return ast.Constant(value=data["value"], kind=None)
    if kind == "Name":
        return ast.Name(id=data["id"], ctx=ast.Load())
    if kind == "Call":
        return ast.Call(
            func=_expr_from_json(data["func"]),
            args=[_expr_from_json(item) for item in data["args"]],
            keywords=[],
        )
    if kind == "Attribute":
        return ast.Attribute(value=_expr_from_json(data["value"]), attr=data["attr"], ctx=ast.Load())
    if kind == "Subscript":
        return ast.Subscript(
            value=_expr_from_json(data["value"]),
            slice=_expr_from_json(data["slice"]),
            ctx=ast.Load(),
        )
    if kind == "UnaryOp":
        return ast.UnaryOp(op=_unary_op(data["op"]), operand=_expr_from_json(data["operand"]))
    if kind == "BinOp":
        return ast.BinOp(
            left=_expr_from_json(data["left"]),
            op=_bin_op(data["op"]),
            right=_expr_from_json(data["right"]),
        )
    if kind == "BoolOp":
        return ast.BoolOp(op=_bool_op(data["op"]), values=[_expr_from_json(item) for item in data["values"]])
    if kind == "Compare":
        return ast.Compare(
            left=_expr_from_json(data["left"]),
            ops=[_cmp_op(str(x)) for x in data["ops"]],
            comparators=[_expr_from_json(item) for item in data["comparators"]],
        )
    if kind == "Match":
        return ast.Match(
            subject=_expr_from_json(data["subject"]),
            cases=[_case_from_json(item) for item in data["cases"]],
        )
    raise ValueError(f"unsupported expression type: {kind}")


def _pattern_from_json(data: dict[str, Any]) -> ast.pattern:
    kind = data["type"]
    if kind == "MatchAs":
        return ast.MatchAs(pattern=None, name=data.get("name"))
    if kind == "MatchValue":
        value = _expr_from_json(data["value"])
        if not isinstance(value, ast.Constant):
            raise ValueError("MatchValue must contain Constant")
        return ast.MatchValue(value=value)
    raise ValueError(f"unsupported pattern type: {kind}")


def _case_from_json(data: dict[str, Any]) -> ast.match_case:
    if data["type"] != "match_case":
        raise ValueError(f"unsupported case type: {data['type']}")
    return ast.match_case(
        pattern=_pattern_from_json(data["pattern"]),
        guard=None,
        body=[ast.Expr(value=_expr_from_json(data["body"]))],
    )


def _arguments_from_names(names: list[Any]) -> ast.arguments:
    return ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg=str(name), annotation=None, type_comment=None) for name in names],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )


def _set_optional_field(node: ast.AST, name: str, value: Any) -> None:
    if name in getattr(node, "_fields", ()):
        setattr(node, name, value)


def _unary_op(name: str) -> ast.unaryop:
    ops = {
        "Not": ast.Not,
        "UAdd": ast.UAdd,
        "USub": ast.USub,
    }
    return ops[name]()


def _bin_op(name: str) -> ast.operator:
    ops = {
        "Add": ast.Add,
        "Sub": ast.Sub,
        "Mult": ast.Mult,
        "Div": ast.Div,
    }
    return ops[name]()


def _bool_op(name: str) -> ast.boolop:
    ops = {
        "And": ast.And,
        "Or": ast.Or,
    }
    return ops[name]()


def _cmp_op(name: str) -> ast.cmpop:
    ops = {
        "Eq": ast.Eq,
        "NotEq": ast.NotEq,
        "Lt": ast.Lt,
        "LtE": ast.LtE,
        "Gt": ast.Gt,
        "GtE": ast.GtE,
    }
    return ops[name]()
