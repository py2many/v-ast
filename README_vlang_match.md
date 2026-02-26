# VLang Match Expression Parser

This repository now includes a V-based parser that models a statically typed, expression-first subset with `match` as an expression.

## Goals Implemented

- Replaced the experimental `pmatch` idea with `match` expression syntax.
- Excluded dynamic constructs that are hard to compile to static targets (for example, string literals and runtime-only dynamic forms).
- Added a Python wrapper that invokes the V parser and returns Python `ast`-style nodes.
- Added tests that parse expressions and validate AST printing for the new match expression.

## Syntax Supported

- Integer literals and names
- Binary operators: `+`, `-`, `*`, `/`
- Parenthesized expressions
- Match expression:

```text
match <expr> {
  case <pattern> => <expr>,
  ...
}
```

Patterns supported:

- Integer value pattern: `case 1 => ...`
- Name binding pattern: `case x => ...`
- Wildcard pattern: `case _ => ...`

## Quick Run

```bash
python -c "from py_match_parser import parse_expression, ast; m=parse_expression('match x { case 0 => 1, case _ => 2 }'); print(ast.dump(m))"
```

## Tests

```bash
pytest -q tests_vlang_parser/test_parser.py
```
