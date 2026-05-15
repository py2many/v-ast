from __future__ import annotations

import ast as py_ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v_ast import ast, parse_expression, parse_module


def _dump(node: py_ast.AST) -> str:
    return py_ast.dump(node, include_attributes=False)


@pytest.mark.parametrize(
    "source",
    [
        "1",
        "'hello'",
        "x",
        "+x",
        "-x",
        "not x",
        "1 + 2 * 3",
        "(1 + 2) * 3",
        "a - b - c",
        "a / b",
        "a and b and c",
        "a or b or c",
        "a and not b or c",
        "a < b",
        "a <= b > c != d == e >= f",
        "f()",
        "f(1, x + 2)",
        "obj.attr",
        "items[0]",
        "obj.method(1)[2].attr",
    ],
)
def test_expression_matches_builtin_ast(source: str) -> None:
    assert _dump(parse_expression(source)) == _dump(py_ast.parse(source, mode="eval"))


@pytest.mark.parametrize(
    "source",
    [
        "import sys\n",
        "import sys, os.path\n",
        "x = 1 + 2\n",
        "print('hello')\n",
        "pass\n",
        "def f():\n    pass\n",
        "def f(x, y):\n    return x + y\n",
        "class C:\n    pass\n",
        "class C(Base, mixin.Factory):\n    def f(self):\n        return self.value\n",
        "if x:\n    y = 1\nelse:\n    y = 2\n",
        "if x:\n    pass\nelif y:\n    pass\n",
        "while x:\n    break\nelse:\n    pass\n",
        "for item in items:\n    continue\nelse:\n    pass\n",
        "def f(x):\n    if not x or x < 3:\n        return x\n    return\n",
    ],
)
def test_module_matches_builtin_ast(source: str) -> None:
    assert _dump(parse_module(source)) == _dump(py_ast.parse(source))


def test_match_expression_uses_builtin_match_node_shape() -> None:
    parsed = parse_expression("match x:\n    1: x + 1\n    _: 0\n")

    expected = py_ast.Expression(
        body=py_ast.Match(
            subject=py_ast.Name(id="x", ctx=py_ast.Load()),
            cases=[
                py_ast.match_case(
                    pattern=py_ast.MatchValue(value=py_ast.Constant(value=1, kind=None)),
                    guard=None,
                    body=[
                        py_ast.Expr(
                            value=py_ast.BinOp(
                                left=py_ast.Name(id="x", ctx=py_ast.Load()),
                                op=py_ast.Add(),
                                right=py_ast.Constant(value=1, kind=None),
                            )
                        )
                    ],
                ),
                py_ast.match_case(
                    pattern=py_ast.MatchAs(pattern=None, name=None),
                    guard=None,
                    body=[py_ast.Expr(value=py_ast.Constant(value=0, kind=None))],
                ),
            ],
        )
    )

    assert isinstance(parsed.body, ast.Match)
    assert _dump(parsed) == _dump(expected)

