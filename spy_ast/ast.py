from __future__ import annotations

"""Compatibility surface for Python's built-in :mod:`ast` module.

The parser in this package intentionally supports only a subset of Python,
plus documented dialect extensions. For the supported Python subset, returned
nodes should have the same shape as nodes produced by ``ast.parse``.
"""

from ast import *  # noqa: F403

