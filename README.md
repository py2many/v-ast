# spy-ast

`spy-ast` is a parser for a subset of Python containing most commonly
used features that can be translated to compiled languages. It
returns nodes that are compatible with Python's built-in `ast`
module when the input stays within the Python-compatible subset.

For dialect features that Python does not support, the tree can
diverge. For example, `spy-ast` supports `match` as an expression
like many compiled languages do; Python's built-in parser only
accepts `match` as a statement.

We will try to stick to the python subset for compatibility reasons
where possible. We want to reuse as much of the existing python
ecosystem and libraries as possible.

The decisions to diverge are not taken lightly. Only when the
overwhelming consensus of compiled languages differs from python's
choices, we introduce equivalent constructs.

Python was designed to be a beginner friendly language. Static python
as defined in this module is mostly aimed at agents.

## Example

Save this as `dump_ast.py`:

```python
from pathlib import Path
import argparse
import ast
import spy_ast


def parse_source(path: Path) -> ast.Module:
    source = path.read_text()
    return spy_ast.parse_module(source)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="test.py")
    args = parser.parse_args()

    # _ensure_macos_homebrew_lib_path()
    tree = parse_source(Path(args.path))
    print(ast.dump(tree, indent=2))


if __name__ == "__main__":
    main()
```

Create a Python-compatible input file:

```sh
cat > test.py <<'PY'
def score(value):
    if value > 10:
        return value + 1
    return 0


print(score(12))
PY
```

Then parse and dump it:

```sh
python dump_ast.py test.py
```

Because `test.py` uses Python-compatible syntax, its AST shape should
match what you would expect from Python's built-in `ast.parse`.

## Dialect Divergence

`spy-ast` intentionally diverges for syntax outside Python's grammar. For
example, this dialect accepts `match` where an expression is expected:

```python
value = match x:
    1: "one"
    _: "other"
```

That source is not valid Python, so `ast.parse` cannot produce a comparable
built-in AST. In cases like this, `spy-ast` still reuses familiar built-in AST
node shapes where practical, but compatibility with `ast` only applies to the
Python-compatible subset.
