from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


class AST:
    pass


class expr(AST):
    pass


class pattern(AST):
    pass


@dataclass(frozen=True)
class Expression(AST):
    body: expr


@dataclass(frozen=True)
class Constant(expr):
    value: int


@dataclass(frozen=True)
class Name(expr):
    id: str


@dataclass(frozen=True)
class BinOp(expr):
    left: expr
    op: str
    right: expr


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
    if isinstance(node, Expression):
        return f"Expression(body={dump(node.body)})"
    if isinstance(node, Constant):
        return f"Constant(value={node.value})"
    if isinstance(node, Name):
        return f"Name(id='{node.id}')"
    if isinstance(node, BinOp):
        return f"BinOp(left={dump(node.left)}, op='{node.op}', right={dump(node.right)})"
    if isinstance(node, MatchValue):
        return f"MatchValue(value={dump(node.value)})"
    if isinstance(node, MatchAs):
        return f"MatchAs(name={repr(node.name)})"
    if isinstance(node, match_case):
        return f"match_case(pattern={dump(node.pattern)}, body={dump(node.body)})"
    if isinstance(node, Match):
        joined = ", ".join(dump(item) for item in node.cases)
        return f"Match(subject={dump(node.subject)}, cases=[{joined}])"
    raise TypeError(f"Unsupported AST node: {type(node)!r}")
