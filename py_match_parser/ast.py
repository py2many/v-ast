from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union


class AST:
    pass


class stmt(AST):
    pass


class expr(AST):
    pass


class pattern(AST):
    pass


@dataclass(frozen=True)
class Module(AST):
    body: list[stmt]


@dataclass(frozen=True)
class Expression(AST):
    body: expr


@dataclass(frozen=True)
class alias(AST):
    name: str


@dataclass(frozen=True)
class Import(stmt):
    names: list[alias]


@dataclass(frozen=True)
class Expr(stmt):
    value: expr


@dataclass(frozen=True)
class Assign(stmt):
    target: str
    value: expr


@dataclass(frozen=True)
class Pass(stmt):
    pass


@dataclass(frozen=True)
class Break(stmt):
    pass


@dataclass(frozen=True)
class Continue(stmt):
    pass


@dataclass(frozen=True)
class Return(stmt):
    value: Optional[expr]


@dataclass(frozen=True)
class If(stmt):
    test: expr
    body: list[stmt]
    orelse: list[stmt]


@dataclass(frozen=True)
class While(stmt):
    test: expr
    body: list[stmt]
    orelse: list[stmt]


@dataclass(frozen=True)
class For(stmt):
    target: str
    iter: expr
    body: list[stmt]
    orelse: list[stmt]


@dataclass(frozen=True)
class FunctionDef(stmt):
    name: str
    args: list[str]
    body: list[stmt]


@dataclass(frozen=True)
class ClassDef(stmt):
    name: str
    bases: list[expr]
    body: list[stmt]


@dataclass(frozen=True)
class Constant(expr):
    value: Any


@dataclass(frozen=True)
class Name(expr):
    id: str


@dataclass(frozen=True)
class Call(expr):
    func: expr
    args: list[expr]


@dataclass(frozen=True)
class Attribute(expr):
    value: expr
    attr: str


@dataclass(frozen=True)
class Subscript(expr):
    value: expr
    slice: expr


@dataclass(frozen=True)
class UnaryOp(expr):
    op: str
    operand: expr


@dataclass(frozen=True)
class BinOp(expr):
    left: expr
    op: str
    right: expr


@dataclass(frozen=True)
class BoolOp(expr):
    op: str
    values: list[expr]


@dataclass(frozen=True)
class Compare(expr):
    left: expr
    ops: list[str]
    comparators: list[expr]


@dataclass(frozen=True)
class MatchValue(pattern):
    value: Constant


@dataclass(frozen=True)
class MatchAs(pattern):
    name: Optional[str]


@dataclass(frozen=True)
class match_case(AST):
    pattern: Union[MatchValue, MatchAs]
    body: expr


@dataclass(frozen=True)
class Match(expr):
    subject: expr
    cases: list[match_case]


def dump(node: AST) -> str:
    if isinstance(node, Module):
        return f"Module(body=[{', '.join(dump(item) for item in node.body)}])"
    if isinstance(node, Expression):
        return f"Expression(body={dump(node.body)})"
    if isinstance(node, alias):
        return f"alias(name='{node.name}')"
    if isinstance(node, Import):
        return f"Import(names=[{', '.join(dump(item) for item in node.names)}])"
    if isinstance(node, Expr):
        return f"Expr(value={dump(node.value)})"
    if isinstance(node, Assign):
        return f"Assign(target='{node.target}', value={dump(node.value)})"
    if isinstance(node, Pass):
        return "Pass()"
    if isinstance(node, Break):
        return "Break()"
    if isinstance(node, Continue):
        return "Continue()"
    if isinstance(node, Return):
        return f"Return(value={dump(node.value) if node.value is not None else None})"
    if isinstance(node, If):
        return (
            f"If(test={dump(node.test)}, body=[{', '.join(dump(item) for item in node.body)}], "
            f"orelse=[{', '.join(dump(item) for item in node.orelse)}])"
        )
    if isinstance(node, While):
        return (
            f"While(test={dump(node.test)}, body=[{', '.join(dump(item) for item in node.body)}], "
            f"orelse=[{', '.join(dump(item) for item in node.orelse)}])"
        )
    if isinstance(node, For):
        return (
            f"For(target='{node.target}', iter={dump(node.iter)}, body=[{', '.join(dump(item) for item in node.body)}], "
            f"orelse=[{', '.join(dump(item) for item in node.orelse)}])"
        )
    if isinstance(node, FunctionDef):
        return f"FunctionDef(name='{node.name}', args={node.args!r}, body=[{', '.join(dump(item) for item in node.body)}])"
    if isinstance(node, ClassDef):
        return (
            f"ClassDef(name='{node.name}', bases=[{', '.join(dump(item) for item in node.bases)}], "
            f"body=[{', '.join(dump(item) for item in node.body)}])"
        )
    if isinstance(node, Constant):
        return f"Constant(value={node.value!r})"
    if isinstance(node, Name):
        return f"Name(id='{node.id}')"
    if isinstance(node, Call):
        return f"Call(func={dump(node.func)}, args=[{', '.join(dump(item) for item in node.args)}])"
    if isinstance(node, Attribute):
        return f"Attribute(value={dump(node.value)}, attr='{node.attr}')"
    if isinstance(node, Subscript):
        return f"Subscript(value={dump(node.value)}, slice={dump(node.slice)})"
    if isinstance(node, UnaryOp):
        return f"UnaryOp(op='{node.op}', operand={dump(node.operand)})"
    if isinstance(node, BinOp):
        return f"BinOp(left={dump(node.left)}, op='{node.op}', right={dump(node.right)})"
    if isinstance(node, BoolOp):
        return f"BoolOp(op='{node.op}', values=[{', '.join(dump(item) for item in node.values)}])"
    if isinstance(node, Compare):
        return (
            f"Compare(left={dump(node.left)}, ops={node.ops!r}, "
            f"comparators=[{', '.join(dump(item) for item in node.comparators)}])"
        )
    if isinstance(node, MatchValue):
        return f"MatchValue(value={dump(node.value)})"
    if isinstance(node, MatchAs):
        return f"MatchAs(name={repr(node.name)})"
    if isinstance(node, match_case):
        return f"match_case(pattern={dump(node.pattern)}, body={dump(node.body)})"
    if isinstance(node, Match):
        return f"Match(subject={dump(node.subject)}, cases=[{', '.join(dump(item) for item in node.cases)}])"
    raise TypeError(f"Unsupported AST node: {type(node)!r}")
