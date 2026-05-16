"""
lexer/source.py
~~~~~~~~~~~~~~~
Source normalization utilities.

Decoupled from the Lexer itself so anything that needs to read
source text (formatters, linters, etc.) can reuse this layer.
"""

from __future__ import annotations

from io import IOBase
from pathlib import Path
from typing import Iterable, Union

# Anything accepted as raw source input.
SourceLike = Union["Source", IOBase, Path, str, Iterable]


class Source:
    """
    A lazily-loaded source file.

    The file is not read from disk until the first access of
    :attr:`lines`, keeping construction cheap.
    """

    __slots__ = ("path", "_lines", "_loaded")

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self._lines: list[str] | None = None
        self._loaded = False

    @property
    def lines(self) -> list[str]:
        if not self._loaded:
            self._load()
        return self._lines  # type: ignore[return-value]

    def _load(self) -> None:
        self._lines = self.path.read_text(encoding="utf-8").splitlines()
        self._loaded = True

    def __repr__(self) -> str:
        return f"Source({self.path!r})"


def extract(data: SourceLike) -> list[str]:
    """
    Normalize any supported input type into a flat list of source lines.

    Accepted types
    --------------
    Source        Lazily-loaded file wrapper (defined above).
    IOBase        Any open file-like object; closed after reading.
    Path          pathlib.Path — read as UTF-8 text.
    str           Raw source text; split on newlines.
    Iterable      Anything else; each item is coerced to str.
    """
    if isinstance(data, Source):
        return data.lines
    if isinstance(data, IOBase):
        lines = [line.rstrip("\n") for line in data.readlines()]
        data.close()
        return lines
    if isinstance(data, Path):
        return data.read_text(encoding="utf-8").splitlines()
    if isinstance(data, str):
        return data.splitlines()
    if isinstance(data, Iterable):
        return [str(item) for item in data]
    raise TypeError(f"Unsupported source type: {type(data).__name__!r}")


def join_source(data: SourceLike) -> str:
    """Extract lines and join them back into a single string."""
    return "\n".join(extract(data))