from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py_match_parser import ast, parse_expression


def test_parse_arithmetic() -> None:
    parsed = parse_expression("1 + 2 * 3")
    assert isinstance(parsed.body, ast.BinOp)
    assert ast.dump(parsed) == (
        "Expression(body=BinOp(left=Constant(value=1), op='Add', "
        "right=BinOp(left=Constant(value=2), op='Mult', right=Constant(value=3))))"
    )


def test_parse_match_expression_and_dump() -> None:
    source = "match x { case 0 => 10, case y => y + 1, case _ => 99 }"
    parsed = parse_expression(source)
    assert isinstance(parsed.body, ast.Match)
    assert ast.dump(parsed) == (
        "Expression(body=Match(subject=Name(id='x'), cases=["
        "match_case(pattern=MatchValue(value=Constant(value=0)), body=Constant(value=10)), "
        "match_case(pattern=MatchAs(name='y'), body=BinOp(left=Name(id='y'), op='Add', right=Constant(value=1))), "
        "match_case(pattern=MatchAs(name=None), body=Constant(value=99))]))"
    )


def test_old_python_match_statement_syntax_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_expression("match x: case 1: 2")


def test_dynamic_feature_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_expression('"hello"')
