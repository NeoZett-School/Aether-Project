"""
transpiler/core.py
~~~~~~~~~~~~~~~~~~
Python code generator / transpiler.

The :class:`PythonTranspiler` converts the AST produced by
:class:`~parser.core.Parser` into a Python source string.

Improvements over the original
-------------------------------
* ``FunctionDeclarationNode`` is handled directly — no more fragile
  heuristic that stitched ``function`` + ``foo(x)`` + ``BlockNode``
  together across three consecutive generator iterations.

* ``ReturnNode`` is emitted as a proper ``return`` statement.

* ``UnaryExpression`` and ``MemberAccessExpression`` are evaluated
  correctly.

* ``_eval`` raises ``TypeError`` on unrecognised expression types
  rather than silently returning ``None``.

* The public entry point is :meth:`transpile`, which returns the
  complete Python source as a single string.
"""

from ._internal.core import (
    DEFAULT_TRANSLATIONS, PythonTranspiler
)

__all__ = (
    "DEFAULT_TRANSLATIONS", "PythonTranspiler"
)