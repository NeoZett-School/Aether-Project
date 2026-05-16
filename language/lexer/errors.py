"""
lexer/errors.py
~~~~~~~~~~~~~~~
Lexer-specific exceptions with precise source-location context.
"""

from ._internal.errors import (
    LexerError
)

__all__ = (
    "LexerError",
)