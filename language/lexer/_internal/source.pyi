"""
lexer/source.py
~~~~~~~~~~~~~~~
Source normalization utilities.

Decoupled from the Lexer itself so anything that needs to read
source text (formatters, linters, etc.) can reuse this layer.
"""

from __future__ import annotations

from typing import (
    List
)

from io import IOBase
from pathlib import Path
from typing import Iterable, Union

# Anything accepted as raw source input.
SourceLike = Union["Source", IOBase, Path, str, Iterable]


class Source:
    path: Path

    def __init__(self, path: Union[str, Path]) -> None: ...

    @property
    def lines(self) -> List[str]: ...


def extract(data: SourceLike) -> List[str]: ...


def join_source(data: SourceLike) -> str: ...