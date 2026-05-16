"""
lexer/states.py
~~~~~~~~~~~~~~~
Token types and lexer states as proper ``IntEnum`` values.

Using ``IntEnum`` gives us:
- Free ``.name`` / ``.value`` attributes (no custom cache needed).
- Membership tests via ``in`` on sets of token types.
- Readable reprs in error messages.
"""

from ._internal.states import (
    TokenType, LexerState
)

__all__ = (
    "TokenType", "LexerState"
)