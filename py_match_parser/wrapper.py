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
    with tempfile.NamedTemporaryFile("w", suffix=".pm", delete=False) as handle:
        path = Path(handle.name)
        handle.write(source)

    try:
        proc = subprocess.run(
            ["v", "run", str(V_ENTRYPOINT.parent), "--json", str(path)],
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

    payload = json.loads(proc.stdout)
    return ast.Expression(body=_expr_from_json(payload))


def _expr_from_json(data: dict[str, Any]) -> ast.expr:
    kind = data["type"]
    if kind == "Constant":
        return ast.Constant(value=int(data["value"]))
    if kind == "Name":
        return ast.Name(id=data["id"])
    if kind == "BinOp":
        return ast.BinOp(
            left=_expr_from_json(data["left"]),
            op=data["op"],
            right=_expr_from_json(data["right"]),
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
