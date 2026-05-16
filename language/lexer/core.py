"""
lexer/core.py
~~~~~~~~~~~~~
The ``Lexer``: consumes a source string and produces a flat list of
:class:`~lexer.token.Token` objects by applying an ordered sequence
of :class:`~lexer.rules.Rule` objects.
"""

from ._internal.core import (
    Lexer
)

__all__ = (
    "Lexer",
)