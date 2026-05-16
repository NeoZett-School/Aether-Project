"""
parser/core.py
~~~~~~~~~~~~~~
Recursive-descent parser.

Improvements over the original
-------------------------------
* Whitespace and comment tokens are filtered out immediately after
  lexing, so the parser never has to skip them mid-stream.  This
  removes the side-effecting ``_skip_whitespace()`` call that was
  embedded in the ``current`` property.

* ``_peek`` is a simple index calculation with no mutation.

* ``function`` and ``return`` are recognised as first-class grammar
  constructs, producing :class:`~parser.nodes.FunctionDeclarationNode`
  and :class:`~parser.nodes.ReturnNode` rather than being handled
  implicitly in the code-generator.

* Unary prefix operators (``!``, ``-``) are parsed in
  ``_parse_unary``.

* Postfix chains — member access (``a.b``) and calls (``f(x)``) —
  are handled uniformly in ``_parse_postfix``, allowing arbitrary
  nesting like ``obj.method(x).field``.
"""

from ._internal.core import (
    KEYWORDS, Parser
)

__all__ = (
    "KEYWORDS", "Parser"
)