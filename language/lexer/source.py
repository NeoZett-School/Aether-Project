"""
lexer/source.py
~~~~~~~~~~~~~~~
Source normalization utilities.

Decoupled from the Lexer itself so anything that needs to read
source text (formatters, linters, etc.) can reuse this layer.
"""

from ._internal.source import (
    SourceLike, Source, extract, join_source
)

__all__ = (
    "SourceLike", "Source", "extract", "join_source"
)