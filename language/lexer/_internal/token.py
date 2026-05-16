"""
lexer/token.py
~~~~~~~~~~~~~~
The ``Token`` data class produced by the lexer.
"""

from __future__ import annotations

from .states import TokenType


class Token:
    """
    A single lexical unit.

    Attributes
    ----------
    token_type:
        One of the :class:`~lexer.states.TokenType` values.
    lexeme:
        The raw text slice this token was produced from.
    row:
        1-based line number of the first character.
    column:
        1-based column number of the first character.
    """

    __slots__ = ("token_type", "lexeme", "row", "column")

    def __init__(
        self,
        token_type: TokenType,
        lexeme: str,
        row: int,
        column: int,
    ) -> None:
        self.token_type = token_type
        self.lexeme = lexeme
        self.row = row
        self.column = column

    # ``TokenType`` is now an ``IntEnum`` so ``.name`` is built in.
    def __repr__(self) -> str:
        return (
            f"Token("
            f"type={self.token_type.name}, "
            f"lexeme={self.lexeme!r}, "
            f"row={self.row}, "
            f"col={self.column}"
            f")"
        )

    def __str__(self) -> str:
        return self.lexeme