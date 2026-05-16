"""
lexer/rules.py
~~~~~~~~~~~~~~
Lexer rule definitions.

Each ``Rule`` subclass encapsulates *two* responsibilities:

``matches(lexer)``
    Return ``True`` if this rule should handle the lexer's current
    position.  Must be a pure, non-mutating check.

``consume(lexer)``
    Advance the lexer past the matched content and emit the
    appropriate token(s).

Rules are tried in the order they appear in the lexer's rule list, so
higher-priority rules (e.g. ``CommentRule`` before ``OperatorRule``)
must come first.
"""

from ._internal.rules import (
    Rule,
    WhitespaceRule, IdentifierRule, NumberRule, StringRule,
    FStringRule, SeparatorRule, BracketRule, OperatorRule,
    AssignmentRule, CompoundAssignRule, AtRule, WalrusRule, 
    ArrowRule,
    DEFAULT_RULES,
)

__all__ = (
    "Rule",
    "WhitespaceRule", "IdentifierRule", "NumberRule", "StringRule",
    "FStringRule", "SeparatorRule", "BracketRule", "OperatorRule",
    "AssignmentRule", "CompoundAssignRule", "AtRule", "WalrusRule",
    "ArrowRule",
    "DEFAULT_RULES"
)