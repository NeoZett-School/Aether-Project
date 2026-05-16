"""
lexer/source.py
~~~~~~~~~~~~~~~
Source normalization utilities.

Decoupled from the Lexer itself so anything that needs to read
source text (formatters, linters, etc.) can reuse this layer.
"""

from .lexer.source import *