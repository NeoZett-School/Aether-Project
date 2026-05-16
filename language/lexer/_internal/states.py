"""
lexer/states.py
~~~~~~~~~~~~~~~
Token types and lexer states as proper ``IntEnum`` values.

Using ``IntEnum`` gives us:
- Free ``.name`` / ``.value`` attributes (no custom cache needed).
- Membership tests via ``in`` on sets of token types.
- Readable reprs in error messages.
"""

from __future__ import annotations

from enum import IntEnum


class TokenType(IntEnum):
    # ---- core ---------------------------------------------------------------
    IDENTIFIER      = 0x000
    NUMBER          = 0x001
    STRING          = 0x002
    FSTRING         = 0x003     # f"..." interpolated string

    # ---- whitespace / comments ----------------------------------------------
    WHITESPACE = 0x010
    COMMENT    = 0x011

    # ---- operators ----------------------------------------------------------
    OPERATOR   = 0x020

    # ---- assignment ---------------------------------------------------------
    ASSIGN          = 0x030
    COMPOUND_ASSIGN = 0x031     # +=  -=  *=  /=  %=  **=
    WALRUS          = 0x032     # :=

    # ---- separators ---------------------------------------------------------
    COMMA      = 0x040
    COLON      = 0x041
    SEMICOLON  = 0x042
    DOT        = 0x043

    # ---- grouping -----------------------------------------------------------
    LPAREN          = 0x050
    RPAREN          = 0x051
    LBRACE          = 0x052
    RBRACE          = 0x053
    LBRACKET        = 0x054
    RBRACKET        = 0x055
    QUESTION        = 0x056     # ? (ternary)

    # ---- decorators ---------------------------------------------------------
    AT = 0x060

    # ---- arrows -----------------------------------------------------------------
    ARROW           = 0x070     # ->

    # ---- sentinel -----------------------------------------------------------
    EOF        = 0xFFF


class LexerState(IntEnum):
    DEFAULT   = 0x0
    STRING    = 0x1
    COMMENT   = 0x2
    DIRECTIVE = 0x3