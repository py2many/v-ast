"""
Variant of test.py demonstrating nested match expressions.
"""

from __future__ import annotations


def classify(x, y):
    return match x:
        0:
            match y:
                0: 100
                _: 101
        1:
            match y:
                0: 200
                _: 201
        _:
            999


def choose(a, b):
    selected = match a:
        10:
            match b:
                1: 11
                2: 12
                _: 19
        _:
            0
    return selected
