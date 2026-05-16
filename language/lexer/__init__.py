"""
lexer
~~~~~
Tokenization layer.

Quick imports::

    from lexer import Lexer, TokenType, Token, Source
"""

from .core import Lexer
from .source import Source, extract, join_source
from .states import LexerState, TokenType
from .token import Token
from .rules import DEFAULT_RULES, Rule

__all__ = [
    "Lexer",
    "Source",
    "extract",
    "join_source",
    "LexerState",
    "TokenType",
    "Token",
    "DEFAULT_RULES",
    "Rule",
]