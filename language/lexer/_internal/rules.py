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

from __future__ import annotations

from abc import ABC, abstractmethod

from .errors import LexerError
from .states import TokenType


_QUOTES: frozenset[str] = frozenset({'"', "'"})

def _detect_string_prefix(lexer, valid_two: frozenset, valid_one: frozenset) -> str:
    """
    Return the normalised (lowercase) prefix sitting before an opening quote,
    or '' if the current position does not start a prefixed string of this kind.

    ``valid_two`` / ``valid_one`` are the two-char and one-char prefixes this
    particular rule cares about, e.g. ``{"rb", "br"}`` / ``{"r", "b"}``.
    """
    c0 = (lexer.current or "").lower()
    c1 = (lexer.peek(1) or "").lower()
    c2 =  lexer.peek(2) or ""
    if c0 + c1 in valid_two and c2 in _QUOTES:
        return c0 + c1
    if c0 in valid_one and c1 in _QUOTES:
        return c0
    return ""


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Rule(ABC):
    """Abstract base for all lexer rules."""

    @abstractmethod
    def matches(self, lexer) -> bool:
        """Return True if this rule applies at the current lexer position."""
        ...

    @abstractmethod
    def consume(self, lexer) -> None:
        """Advance the lexer and emit one or more tokens."""
        ...


# ---------------------------------------------------------------------------
# Concrete rules
# ---------------------------------------------------------------------------


class WhitespaceRule(Rule):
    """Consumes any run of whitespace characters as a single token."""

    def matches(self, lexer) -> bool:
        return lexer.current is not None and lexer.current.isspace()

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        lexeme = lexer.consume_while(str.isspace)
        lexer.emit(TokenType.WHITESPACE, lexeme, row, column)


class CommentRule(Rule):
    """
    Consumes a single-line comment introduced by ``//``.

    Must appear *before* ``OperatorRule`` in the rule list so that
    the ``/`` character is not greedily consumed as a division
    operator.
    """

    def matches(self, lexer) -> bool:
        return lexer.match_sequence("//")

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        # Consume everything up to (but not including) the newline.
        lexeme = lexer.consume_while(lambda c: c != "\n")
        lexer.emit(TokenType.COMMENT, lexeme, row, column)


class IdentifierRule(Rule):
    """
    Consumes identifiers: ``[a-zA-Z_][a-zA-Z0-9_]*``.

    Keywords are represented as ordinary IDENTIFIER tokens; the
    parser is responsible for giving them special meaning.
    """

    def matches(self, lexer) -> bool:
        c = lexer.current
        return c is not None and (c.isalpha() or c == "_")

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        lexeme = lexer.consume_while(lambda c: c.isalnum() or c == "_")
        lexer.emit(TokenType.IDENTIFIER, lexeme, row, column)


class NumberRule(Rule):
    """
    Consumes integer and floating-point numeric literals.

    Accepts an optional single decimal point, e.g. ``3``, ``3.14``.
    Consecutive dots are handled gracefully by stopping at the
    second one.
    """

    def matches(self, lexer) -> bool:
        return lexer.current is not None and lexer.current.isdigit()

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        lexeme = ""
        seen_dot = False

        while lexer.current is not None:
            if lexer.current.isdigit():
                lexeme += lexer.advance()
            elif lexer.current == "." and not seen_dot:
                seen_dot = True
                lexeme += lexer.advance()
            else:
                break

        lexer.emit(TokenType.NUMBER, lexeme, row, column)


class StringRule(Rule):
    """
    Consumes plain and prefixed non-f-string literals.

    Supported prefixes (case-insensitive, stored normalised to lowercase):
      r / R          raw  — backslashes are not processed
      b / B          bytes
      rb / br / RB … raw bytes
    """

    _TWO = frozenset({"rb", "br"})
    _ONE = frozenset({"r", "b"})

    ESCAPES: dict[str, str] = {
        "n": "\n", "t": "\t", "r": "\r",
        "\\": "\\", '"': '"', "'": "'",
    }

    def matches(self, lexer) -> bool:
        return (
            lexer.current in _QUOTES
            or bool(_detect_string_prefix(lexer, self._TWO, self._ONE))
        )

    def consume(self, lexer) -> None:
        from .errors import LexerError
        row, column = lexer.row, lexer.column

        prefix = _detect_string_prefix(lexer, self._TWO, self._ONE)
        for _ in prefix:                    # advance past prefix chars
            lexer.advance()

        is_raw = "r" in prefix
        quote  = lexer.advance()            # opening quote
        lexeme = ""

        while lexer.current is not None:
            c = lexer.current

            if c == quote:
                lexer.advance()
                lexer.emit(TokenType.STRING, lexeme, row, column, prefix)
                return

            if not is_raw and c == "\\":
                lexer.advance()
                esc = lexer.current
                if esc is None:
                    raise LexerError("Unterminated escape sequence", lexer.row, lexer.column)
                lexeme += self.ESCAPES.get(esc, "\\" + esc)
                lexer.advance()
                continue

            lexeme += lexer.advance()

        raise LexerError("Unterminated string literal", row, column)


class FStringRule(Rule):
    """
    Consumes interpolated string literals.

    Supported prefixes (case-insensitive, stored normalised):
      f / F          standard f-string
      rf / fr / RF … raw f-string — backslashes in literal segments are verbatim

    The entire content between the quotes is stored as the lexeme; the
    parser splits and recurses into ``{...}`` placeholders.
    Must be registered *before* StringRule and IdentifierRule.
    """

    _TWO = frozenset({"rf", "fr"})
    _ONE = frozenset({"f"})

    def matches(self, lexer) -> bool:
        return bool(_detect_string_prefix(lexer, self._TWO, self._ONE))

    def consume(self, lexer) -> None:
        from .errors import LexerError
        row, column = lexer.row, lexer.column

        prefix = _detect_string_prefix(lexer, self._TWO, self._ONE)
        is_raw = "r" in prefix

        for _ in prefix:
            lexer.advance()

        quote = lexer.advance()             # opening quote
        raw   = ""

        while lexer.current is not None:
            if lexer.current == quote:
                lexer.advance()
                lexer.emit(TokenType.FSTRING, raw, row, column, prefix)
                return
            # In non-raw f-strings keep escaped quotes/backslashes verbatim
            # so the parser sees them intact when it recurses into placeholders.
            if not is_raw and lexer.current == "\\" and lexer.peek() in (quote, "\\"):
                raw += lexer.advance()
                raw += lexer.advance()
                continue
            raw += lexer.advance()

        raise LexerError("Unterminated f-string", row, column)


class SeparatorRule(Rule):
    """Consumes punctuation that separates or terminates constructs."""

    SEPARATORS: dict[str, TokenType] = {
        ",": TokenType.COMMA,
        ":": TokenType.COLON,
        ";": TokenType.SEMICOLON,
        ".": TokenType.DOT,
        "?": TokenType.QUESTION
    }

    def matches(self, lexer) -> bool:
        return lexer.current in self.SEPARATORS

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        char = lexer.advance()
        lexer.emit(self.SEPARATORS[char], char, row, column)


class BracketRule(Rule):
    """Consumes opening and closing bracket characters."""

    BRACKETS: dict[str, TokenType] = {
        "(": TokenType.LPAREN,
        ")": TokenType.RPAREN,
        "{": TokenType.LBRACE,
        "}": TokenType.RBRACE,
        "[": TokenType.LBRACKET,
        "]": TokenType.RBRACKET,
    }

    def matches(self, lexer) -> bool:
        return lexer.current in self.BRACKETS

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        char = lexer.advance()
        lexer.emit(self.BRACKETS[char], char, row, column)


class OperatorRule(Rule):
    """
    Consumes one- and two-character operators.

    Two-character operators take priority: the rule checks for them
    first so that ``==`` is not consumed as two separate ``=`` tokens.

    Note: ``CommentRule`` must precede this rule in the rule list so
    that ``//`` is recognized as a comment rather than two divisions.
    """

    DOUBLE: frozenset[str] = frozenset({
        "==", "!=", "<=", ">=", "&&", "||", "++", "--", "**",
    })

    SINGLE: frozenset[str] = frozenset({
        "+", "-", "*", "/", "%", "<", ">", "!",
    })

    def matches(self, lexer) -> bool:
        c = lexer.current
        if c is None:
            return False
        pair = c + (lexer.peek() or "")
        return pair in self.DOUBLE or c in self.SINGLE

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        pair = lexer.current + (lexer.peek() or "")

        if pair in self.DOUBLE:
            lexeme = lexer.advance() + lexer.advance()
        else:
            lexeme = lexer.advance()

        lexer.emit(TokenType.OPERATOR, lexeme, row, column)


class AssignmentRule(Rule):
    """
    Consumes a bare ``=`` assignment operator.

    Must appear *before* ``OperatorRule`` in the rule list.
    ``OperatorRule`` does not consume ``=`` by itself, but this
    ordering makes the intent explicit.
    """

    def matches(self, lexer) -> bool:
        return lexer.current == "=" and lexer.peek() != "="

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        lexer.emit(TokenType.ASSIGN, lexer.advance(), row, column)


class CompoundAssignRule(Rule):
    """Consumes compound assignment operators: ``+=``, ``-=``, ``*=``, ``/=``, ``%=``, ``**=``."""

    _THREE = frozenset({"**="})
    _TWO   = frozenset({"+=", "-=", "*=", "/=", "%="})

    def matches(self, lexer) -> bool:
        two   = (lexer.current or "") + (lexer.peek(1) or "")
        three = two + (lexer.peek(2) or "")
        return three in self._THREE or two in self._TWO

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        two   = (lexer.current or "") + (lexer.peek(1) or "")
        three = two + (lexer.peek(2) or "")
        if three in self._THREE:
            lexeme = lexer.advance() + lexer.advance() + lexer.advance()
        else:
            lexeme = lexer.advance() + lexer.advance()
        lexer.emit(TokenType.COMPOUND_ASSIGN, lexeme, row, column)


class AtRule(Rule):
    """Consumes the '@' decorator sigil."""

    def matches(self, lexer) -> bool:
        return lexer.current == "@"

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        lexer.emit(TokenType.AT, lexer.advance(), row, column)


class WalrusRule(Rule):
    """
    Consumes ``:=``.

    Must precede ``SeparatorRule``, which would otherwise consume the
    ``:`` as COLON before the ``=`` is seen.
    """

    def matches(self, lexer) -> bool:
        return lexer.current == ":" and lexer.peek() == "="

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        lexer.advance()
        lexer.advance()
        lexer.emit(TokenType.WALRUS, ":=", row, column)


class ArrowRule(Rule):
    """
    Consumes ``->``.

    Must precede ``OperatorRule``, which would otherwise consume ``-``
    as a lone subtraction operator.
    """

    def matches(self, lexer) -> bool:
        return lexer.current == "-" and lexer.peek() == ">"

    def consume(self, lexer) -> None:
        row, column = lexer.row, lexer.column
        lexer.advance()
        lexer.advance()
        lexer.emit(TokenType.ARROW, "->", row, column)


# ---------------------------------------------------------------------------
# Canonical rule ordering
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[Rule] = [
    WhitespaceRule(),
    CommentRule(),
    FStringRule(),
    AtRule(),
    StringRule(),
    IdentifierRule(),
    NumberRule(),
    WalrusRule(),
    SeparatorRule(),
    BracketRule(),
    CompoundAssignRule(),
    ArrowRule(),
    AssignmentRule(),
    OperatorRule(),
]