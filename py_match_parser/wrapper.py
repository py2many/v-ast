from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import ast


ROOT = Path(__file__).resolve().parents[1]
V_ENTRYPOINT = ROOT / "vlang_match_parser" / "main.v"


def parse_expression(source: str) -> ast.Expression:
    payload = _run_parser("--json-expr", source)
    return ast.Expression(body=_expr_from_json(payload))


def parse_module(source: str) -> ast.Module:
    payload = _run_parser("--json", source)
    if payload.get("type") != "Module":
        raise ValueError(f"expected Module payload, got {payload.get('type')}")
    return ast.Module(body=[_stmt_from_json(item) for item in payload["body"]])


def _run_parser(mode: str, source: str) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        path = Path(handle.name)
        handle.write(source)

    try:
        proc = subprocess.run(
            ["v", "run", str(V_ENTRYPOINT.parent), mode, str(path)],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
    finally:
        path.unlink(missing_ok=True)

    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "unknown parser failure"
        raise ValueError(message)

    return json.loads(proc.stdout)


def _stmt_from_json(data: dict[str, Any]) -> ast.stmt:
    kind = data["type"]
    if kind == "Import":
        return ast.Import(names=[ast.alias(name=item["name"]) for item in data["names"]])
    if kind == "Expr":
        return ast.Expr(value=_expr_from_json(data["value"]))
    if kind == "Assign":
        return ast.Assign(target=data["target"], value=_expr_from_json(data["value"]))
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
            target=data["target"],
            iter=_expr_from_json(data["iter"]),
            body=[_stmt_from_json(item) for item in data["body"]],
            orelse=[_stmt_from_json(item) for item in data["orelse"]],
        )
    if kind == "FunctionDef":
        return ast.FunctionDef(
            name=data["name"],
            args=[str(x) for x in data["args"]],
            body=[_stmt_from_json(item) for item in data["body"]],
        )
    if kind == "ClassDef":
        return ast.ClassDef(
            name=data["name"],
            bases=[_expr_from_json(item) for item in data["bases"]],
            body=[_stmt_from_json(item) for item in data["body"]],
        )
    raise ValueError(f"unsupported statement type: {kind}")


def _expr_from_json(data: dict[str, Any]) -> ast.expr:
    kind = data["type"]
    if kind == "Constant":
        return ast.Constant(value=data["value"])
    if kind == "Name":
        return ast.Name(id=data["id"])
    if kind == "Call":
        return ast.Call(
            func=_expr_from_json(data["func"]),
            args=[_expr_from_json(item) for item in data["args"]],
        )
    if kind == "Attribute":
        return ast.Attribute(value=_expr_from_json(data["value"]), attr=data["attr"])
    if kind == "Subscript":
        return ast.Subscript(value=_expr_from_json(data["value"]), slice=_expr_from_json(data["slice"]))
    if kind == "UnaryOp":
        return ast.UnaryOp(op=data["op"], operand=_expr_from_json(data["operand"]))
    if kind == "BinOp":
        return ast.BinOp(
            left=_expr_from_json(data["left"]),
            op=data["op"],
            right=_expr_from_json(data["right"]),
        )
    if kind == "BoolOp":
        return ast.BoolOp(op=data["op"], values=[_expr_from_json(item) for item in data["values"]])
    if kind == "Compare":
        return ast.Compare(
            left=_expr_from_json(data["left"]),
            ops=[str(x) for x in data["ops"]],
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
        return ast.MatchAs(name=data.get("name"))
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
        body=_expr_from_json(data["body"]),
    )
