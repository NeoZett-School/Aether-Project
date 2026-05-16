"""
parser/errors.py
~~~~~~~~~~~~~~~~
Parser-specific exceptions with precise source-location context.
"""

from __future__ import annotations


class ParseError(Exception):
    """
    Raised when the parser encounters a token or structure it cannot
    handle.

    Parameters
    ----------
    message:
        Human-readable description of the problem.
    row:
        1-based line number (optional; ``None`` if unknown).
    column:
        1-based column number (optional; ``None`` if unknown).
    """

    def __init__(
        self,
        message: str,
        row: int | None = None,
        column: int | None = None,
    ) -> None:
        self.row = row
        self.column = column
        location = f" at row {row}, column {column}" if row is not None else ""
        super().__init__(f"{message}{location}")