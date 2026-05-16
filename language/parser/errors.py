"""
parser/errors.py
~~~~~~~~~~~~~~~~
Parser-specific exceptions with precise source-location context.
"""

from ._internal.errors import (
    ParseError
)

__all__ = (
    "ParseError",
)