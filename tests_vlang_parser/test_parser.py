from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py_match_parser import ast, parse_expression, parse_module


def test_parse_arithmetic() -> None:
    parsed = parse_expression("1 + 2 * 3")
    assert isinstance(parsed.body, ast.BinOp)


def test_parse_match_expression_and_dump() -> None:
    source = "match x:\n    0: 10\n    y: y + 1\n    _: 99\n"
    parsed = parse_expression(source)
    assert isinstance(parsed.body, ast.Match)
    dumped = ast.dump(parsed)
    assert "Match(subject=Name(id='x')" in dumped
    assert "match_case(pattern=MatchValue(value=Constant(value=0))" in dumped


def test_parse_module_import_and_call() -> None:
    source = 'import sys\nprint("hello")\n'
    parsed = parse_module(source)
    assert ast.dump(parsed) == (
        "Module(body=[Import(names=[alias(name='sys')]), "
        "Expr(value=Call(func=Name(id='print'), args=[Constant(value='hello')]))])"
    )


def test_control_flow_defs_and_expr_features() -> None:
    source = (
        "class C(Base):\n"
        "    def f(x, y):\n"
        "        if not x or y < 3:\n"
        "            return x.attr[0] + y\n"
        "        else:\n"
        "            while x:\n"
        "                for i in y:\n"
        "                    continue\n"
        "                break\n"
        "            return\n"
    )
    parsed = parse_module(source)
    dumped = ast.dump(parsed)
    assert "ClassDef(name='C'" in dumped
    assert "FunctionDef(name='f', args=['x', 'y']" in dumped
    assert "If(test=BoolOp(op='Or'" in dumped
    assert "UnaryOp(op='Not'" in dumped
    assert "Compare(left=Name(id='y'), ops=['Lt']" in dumped
    assert "Subscript(value=Attribute(value=Name(id='x'), attr='attr'), slice=Constant(value=0))" in dumped
    assert "While(test=Name(id='x')" in dumped
    assert "For(target='i', iter=Name(id='y')" in dumped
    assert "Continue()" in dumped
    assert "Break()" in dumped
    assert "Return(value=None)" in dumped


def test_indentation_based_match_expression() -> None:
    source = (
        "x = 2\n"
        "y = match x:\n"
        "    1: 10\n"
        "    _: 0\n"
        "print(y)\n"
    )
    parsed = parse_module(source)
    dumped = ast.dump(parsed)
    assert "Assign(target='y', value=Match(subject=Name(id='x')" in dumped
    assert "MatchAs(name=None)" in dumped


def test_old_python_match_statement_syntax_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_expression("match x: case 1: 2")


def test_arrow_style_match_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_expression("match x { 1 => 10, _ => 0 }")


def test_brace_style_match_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_expression("match x { 1: 10, _: 0 }")


def test_parse_repository_test_py_module() -> None:
    source = Path(__file__).resolve().parents[1] / "test.py"
    parsed = parse_module(source.read_text())
    assert isinstance(parsed, ast.Module)
    assert len(parsed.body) > 0


def test_parse_nested_match_variant_module() -> None:
    source = Path(__file__).resolve().parents[1] / "test_nested_match.py"
    parsed = parse_module(source.read_text())
    dumped = ast.dump(parsed)
    assert dumped.count("Match(subject=") >= 3
