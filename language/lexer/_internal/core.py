"""
lexer/core.py
~~~~~~~~~~~~~
The ``Lexer``: consumes a source string and produces a flat list of
:class:`~lexer.token.Token` objects by applying an ordered sequence
of :class:`~lexer.rules.Rule` objects.
"""

from __future__ import annotations

from .errors import LexerError
from .rules import Rule, DEFAULT_RULES
from .source import SourceLike, extract
from .states import LexerState, TokenType
from .token import Token


class Lexer:
    """
    Character-stream tokenizer.

    Parameters
    ----------
    data:
        Any :data:`~lexer.source.SourceLike` value — a file path,
        open stream, raw string, or iterable of lines.
    rules:
        Ordered list of :class:`~lexer.rules.Rule` objects to apply.
        Defaults to :data:`~lexer.rules.DEFAULT_RULES`.

    Usage
    -----
    ::

        from lexer.core import Lexer
        tokens = Lexer("x = 1 + 2").tokenize()
    """

    __slots__ = (
        "source",
        "rules",
        "index",
        "row",
        "column",
        "_tokens",
        "state",
    )

    def __init__(
        self,
        data: SourceLike,
        *,
        rules: list[Rule] | None = None,
    ) -> None:
        lines = extract(data)
        self.source: str = "\n".join(lines)
        self.rules: list[Rule] = rules if rules is not None else DEFAULT_RULES
        self.index: int = 0
        self.row: int = 1
        self.column: int = 1
        self._tokens: list[Token] = []
        self.state: LexerState = LexerState.DEFAULT

    # ---------------------------------------------------------------- cursor

    @property
    def current(self) -> str | None:
        """Character at the current position, or ``None`` at EOF."""
        if self.index >= len(self.source):
            return None
        return self.source[self.index]

    def peek(self, offset: int = 1) -> str | None:
        """Character ``offset`` positions ahead, or ``None`` past EOF."""
        idx = self.index + offset
        if idx >= len(self.source):
            return None
        return self.source[idx]

    def advance(self) -> str:
        """
        Consume and return the current character, updating row/column
        tracking.
        """
        char = self.current
        if char is None:
            raise LexerError("Unexpected end of source", self.row, self.column)
        self.index += 1
        if char == "\n":
            self.row += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def match(self, char: str) -> bool:
        """Return ``True`` if the current character equals *char*."""
        return self.current == char

    def match_sequence(self, sequence: str) -> bool:
        """Return ``True`` if the source ahead equals *sequence*."""
        end = self.index + len(sequence)
        return self.source[self.index:end] == sequence

    def consume_while(self, predicate) -> str:
        """
        Advance while *predicate(current)* is truthy and return the
        consumed substring.
        """
        lexeme = ""
        while self.current is not None and predicate(self.current):
            lexeme += self.advance()
        return lexeme

    # ----------------------------------------------------------------- emit

    def emit(
        self,
        token_type: TokenType,
        lexeme: str,
        row: int,
        column: int,
    ) -> None:
        """Append a new :class:`~lexer.token.Token` to the token list."""
        self._tokens.append(Token(token_type, lexeme, row, column))

    # --------------------------------------------------------------- tokenize

    def tokenize(self) -> list[Token]:
        """
        Run all rules over the source and return the complete token list
        (including a terminal ``EOF`` token).

        Raises
        ------
        LexerError
            If no rule matches the current character.
        """
        while self.current is not None:
            matched = False
            for rule in self.rules:
                if rule.matches(self):
                    rule.consume(self)
                    matched = True
                    break

            if not matched:
                raise LexerError(
                    f"Unexpected character {self.current!r}",
                    self.row,
                    self.column,
                )

        self.emit(TokenType.EOF, "", self.row, self.column)
        return self._tokens 