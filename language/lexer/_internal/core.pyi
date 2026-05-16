"""
lexer/core.py
~~~~~~~~~~~~~
The ``Lexer``: consumes a source string and produces a flat list of
:class:`~lexer.token.Token` objects by applying an ordered sequence
of :class:`~lexer.rules.Rule` objects.
"""

from __future__ import annotations

from typing import (
    List, Callable
)

from .rules import Rule
from .source import SourceLike
from .states import LexerState, TokenType
from .token import Token


class Lexer:
    source: str
    rules: List[Rule]
    index: int
    row: int
    column: int
    state: LexerState

    def __init__(
        self,
        data: SourceLike,
        *,
        rules: List[Rule] | None = None,
    ) -> None: ...

    # ---------------------------------------------------------------- cursor

    @property
    def current(self) -> str | None: ...

    def peek(self, offset: int = 1) -> str | None: ...

    def advance(self) -> str: ...

    def match(self, char: str) -> bool: ...

    def match_sequence(self, sequence: str) -> bool: ...

    def consume_while(self, predicate: Callable) -> str: ...

    # ----------------------------------------------------------------- emit

    def emit(
        self,
        token_type: TokenType,
        lexeme: str,
        row: int,
        column: int,
    ) -> None: ...

    # --------------------------------------------------------------- tokenize

    def tokenize(self) -> list[Token]: ...