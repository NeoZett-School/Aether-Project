"""
lexer/errors.py
~~~~~~~~~~~~~~~
Lexer-specific exceptions with precise source-location context.
"""

from __future__ import annotations


class LexerError(Exception):
    """
    Raised when the lexer encounters a character or sequence it cannot
    tokenize.

    Parameters
    ----------
    message:
        Human-readable description of the problem.
    row:
        1-based line number in the source.
    column:
        1-based column number in the source.
    """

    def __init__(self, message: str, row: int, column: int) -> None:
        self.row = row
        self.column = column
        super().__init__(f"{message} at row {row}, column {column}")