"""
parser/core.py
~~~~~~~~~~~~~~
Recursive-descent parser.

Improvements over the original
-------------------------------
* Whitespace and comment tokens are filtered out immediately after
  lexing, so the parser never has to skip them mid-stream.  This
  removes the side-effecting ``_skip_whitespace()`` call that was
  embedded in the ``current`` property.

* ``_peek`` is a simple index calculation with no mutation.

* ``function`` and ``return`` are recognised as first-class grammar
  constructs, producing :class:`~parser.nodes.FunctionDeclarationNode`
  and :class:`~parser.nodes.ReturnNode` rather than being handled
  implicitly in the code-generator.

* Unary prefix operators (``!``, ``-``) are parsed in
  ``_parse_unary``.

* Postfix chains — member access (``a.b``) and calls (``f(x)``) —
  are handled uniformly in ``_parse_postfix``, allowing arbitrary
  nesting like ``obj.method(x).field``.
"""

from __future__ import annotations

from ...lexer.core import Lexer
from ...lexer.states import TokenType
from ...lexer.token import Token
from .errors import ParseError
from .nodes import (
    Parameter,
    Argument,
    Decorator,
    ArrayExpression,
    AssignmentNode,
    CompoundAssignmentNode,
    AnnotatedAssignmentNode,
    WithItem,
    WithNode,
    AssertNode,
    BinaryExpression,
    BlockNode,
    CallExpression,
    SubscriptExpression,
    Expression,
    ExpressionNode,
    FunctionDeclarationNode,
    ClassDeclarationNode,
    TupleExpression,
    StarExpression,
    FStringPart,
    FStringExpression,
    TernaryExpression,
    WalrusExpression,
    GroupExpression,
    Identifier,
    Literal,
    MemberAccessExpression,
    Node,
    ReturnNode,
    RaiseNode,
    UnaryExpression,
    ImportNode,
    FromImportNode,
    IfNode,
    ForNode,
    WhileNode,
    ExceptHandler,
    TryNode,
    BreakNode,
    ContinueNode,
    PassNode,
    Pattern,
    LiteralPattern,
    CapturePattern,
    WildcardPattern,
    ValuePattern,
    OrPattern,
    CaseClause,
    SwitchNode,
)

# Token types that carry no semantic meaning and can be stripped.
_NOISE: frozenset[TokenType] = frozenset({
    TokenType.WHITESPACE,
    TokenType.COMMENT,
})

# Identifiers that the parser treats as keywords.
KEYWORDS: frozenset[str] = frozenset({
    "function", "return", "class", "extends",
    "if", "elif", "else",
    "for", "while", "in",
    "try", "except", "finally",
    "import", "from", "as",
    "not", "and", "or", "is",
    "break", "continue", "pass",
    "with", "assert",
    "switch", "case", "default"
})


class Parser:
    """
    Produces an AST from the token stream of a :class:`~lexer.core.Lexer`.

    Usage
    -----
    ::

        lexer  = Lexer("function add(a, b) { return a + b; }")
        parser = Parser(lexer).load()
        nodes  = parser.parse()
    """

    __slots__ = ("_lexer", "_tokens", "_index", "nodes")

    def __init__(self, lexer: Lexer) -> None:
        self._lexer = lexer
        self._tokens: list[Token] = []
        self._index: int = 0
        self.nodes: list[Node] = []

    # ------------------------------------------------------------------ setup

    def load(self) -> "Parser":
        """
        Lex the source and store the filtered token stream.
        Returns ``self`` to allow method chaining.
        """
        self._tokens = [
            tok
            for tok in self._lexer.tokenize()
            if tok.token_type not in _NOISE
        ]
        return self

    # ----------------------------------------------------------- token access

    @property
    def _current(self) -> Token | None:
        """The token at the current position, or ``None`` past the end."""
        return self._tokens[self._index] if self._index < len(self._tokens) else None

    def _peek(self, offset: int = 1) -> Token | None:
        """Token *offset* positions ahead, without mutating state."""
        idx = self._index + offset
        return self._tokens[idx] if idx < len(self._tokens) else None

    def _advance(self) -> Token:
        """Consume and return the current token."""
        tok = self._current
        if tok is None:
            raise ParseError("Unexpected end of input")
        self._index += 1
        return tok

    def _match(self, *types: TokenType) -> bool:
        """Return ``True`` if the current token has one of the given types."""
        return self._current is not None and self._current.token_type in types

    def _match_keyword(self, *keywords: str) -> bool:
        """Return ``True`` if the current token is a specific keyword identifier."""
        tok = self._current
        return (
            tok is not None
            and tok.token_type == TokenType.IDENTIFIER
            and tok.lexeme in keywords
        )

    def _expect(self, token_type: TokenType) -> Token:
        """
        Consume and return the current token, raising :exc:`ParseError`
        if its type does not match *token_type*.
        """
        tok = self._current
        if tok is None or tok.token_type != token_type:
            got = repr(tok) if tok else "EOF"
            raise ParseError(
                f"Expected {token_type.name}, got {got}",
                tok.row if tok else None,
                tok.column if tok else None,
            )
        return self._advance()

    def _optional(self, token_type: TokenType) -> Token | None:
        """Consume and return the current token only if it matches, else ``None``."""
        if self._match(token_type):
            return self._advance()
        return None

    # ----------------------------------------------------------------- parse

    def parse(self) -> list[Node]:
        """
        Parse all statements until ``EOF`` and return the node list.
        Also stored in :attr:`nodes`.
        """
        self.nodes = []
        while self._current and self._current.token_type != TokenType.EOF:
            self.nodes.append(self._parse_statement())
        return self.nodes

    # ----------------------------------------------------------- statements

    def _parse_statement(self) -> Node:
        # ── decorators: @name lines before a declaration ──────────────────────
        decorators: list[str] = []
        while self._match(TokenType.AT):
            self._advance()                           # consume `@`
            decorators.append(Decorator(self._parse_postfix()))

        # ── keyword: function declaration ──────────────────────────────────
        if self._match_keyword("function"):
            return self._parse_function_declaration(decorators)
        
        # ── keyword: class declaration ─────────────────────────────────────
        if self._match_keyword("class"):
            return self._parse_class_declaration(decorators)
        
        if decorators:
            tok = self._current
            raise ParseError(
                "Decorators must precede a function or class declaration",
                tok.row if tok else None,
                tok.column if tok else None,
            )

        # ── keyword: return ────────────────────────────────────────────────
        if self._match_keyword("return"):
            return self._parse_return()
        
        if self._match_keyword("raise"):
            return self._parse_raise()

        # ── block ─────────────────────────────────────────────────────────
        if self._match(TokenType.LBRACE):
            return self._parse_block()
        
        # ── other statements ───────────────────────────────────────────────

        if self._match_keyword("import"):   return self._parse_import()
        if self._match_keyword("from"):     return self._parse_from_import()
        if self._match_keyword("if"):       return self._parse_if()
        if self._match_keyword("for"):      return self._parse_for()
        if self._match_keyword("while"):    return self._parse_while()
        if self._match_keyword("try"):      return self._parse_try()
        if self._match_keyword("with"):     return self._parse_with()
        if self._match_keyword("assert"):   return self._parse_assert()
        if self._match_keyword("switch"):   return self._parse_switch()

        if self._match_keyword("break"):
            self._advance(); self._optional(TokenType.SEMICOLON); return BreakNode()

        if self._match_keyword("continue"):
            self._advance(); self._optional(TokenType.SEMICOLON); return ContinueNode()

        if self._match_keyword("pass"):
            self._advance(); self._optional(TokenType.SEMICOLON); return PassNode()
        
        # Parse any expression (identifier, member chain, subscript, call, …)
        expr = self._parse_expression()

        # ── assignment: <identifier> = <expr> ─────────────────────────────
        # Then decide what kind of statement it is based on what follows.
        if self._match(TokenType.ASSIGN):
            self._validate_target(expr)
            self._advance()                         # consume `=`
            value = self._parse_expression()
            self._optional(TokenType.SEMICOLON)
            return AssignmentNode(expr, value)

        if self._match(TokenType.COMPOUND_ASSIGN):
            self._validate_target(expr)
            op = self._advance().lexeme             # consume `+=` etc.
            value = self._parse_expression()
            self._optional(TokenType.SEMICOLON)
            return CompoundAssignmentNode(expr, op, value)
        
        if self._match(TokenType.COLON):
            self._validate_target(expr)
            self._advance()                         # consume ':'
            annotation = self._parse_annotation()
            value = None
            if self._match(TokenType.ASSIGN):
                self._advance()
                value = self._parse_expression()
            self._optional(TokenType.SEMICOLON)
            return AnnotatedAssignmentNode(expr, annotation, value)

        # ── expression statement ───────────────────────────────────────────
        self._optional(TokenType.SEMICOLON)
        return ExpressionNode(expr)
    
    _ASSIGNABLE = (Identifier, MemberAccessExpression, SubscriptExpression)

    def _validate_target(self, expr: Expression) -> None:
        """Raise ParseError if ``expr`` is not a legal assignment target."""
        if isinstance(expr, self._ASSIGNABLE):
            return
        if isinstance(expr, (TupleExpression, ArrayExpression)):
            for e in expr.elements:
                if not isinstance(e, StarExpression):
                    self._validate_target(e)
            return
        raise ParseError(
            f"Invalid assignment target: {type(expr).__name__} — "
            f"expected a variable, member, subscript, or destructuring pattern"
        )
    
    def _parse_class_declaration(self, decorators: list[str] | None = None) -> ClassDeclarationNode:
        """``class Name [extends Super] { method* }``"""
        self._advance()                                 # consume `class`
        name_tok = self._expect(TokenType.IDENTIFIER)

        bases: list[str] = []
        if self._match_keyword("extends"):
            self._advance()
            bases.append(self._expect(TokenType.IDENTIFIER).lexeme)
            while self._match(TokenType.COMMA):
                self._advance()
                bases.append(self._expect(TokenType.IDENTIFIER).lexeme)

        self._expect(TokenType.LBRACE)
        body: list[Node] = []

        while self._current and not self._match(TokenType.RBRACE):

            # ── decorators ────────────────────────────────────────────────────
            member_decorators: list[Decorator] = []
            while self._match(TokenType.AT):
                self._advance()
                member_decorators.append(Decorator(self._parse_postfix()))

            # ── method declaration ────────────────────────────────────────────
            if self._match_keyword("function"):
                body.append(self._parse_function_declaration(member_decorators))
                continue

            # decorators with no following function are an error
            if member_decorators:
                tok = self._current
                raise ParseError(
                    "Decorators inside a class body must precede a method declaration",
                    tok.row if tok else None,
                    tok.column if tok else None,
                )

            # ── pass ──────────────────────────────────────────────────────────
            if self._match_keyword("pass"):
                self._advance()
                self._optional(TokenType.SEMICOLON)
                body.append(PassNode())
                continue

            # ── assignment / annotated assignment / compound assignment ────────
            # Parse the LHS as an expression first, then decide by what follows.
            expr = self._parse_expression()

            if self._match(TokenType.ASSIGN):
                self._validate_target(expr)
                self._advance()                         # consume `=`
                value = self._parse_expression()
                self._optional(TokenType.SEMICOLON)
                body.append(AssignmentNode(expr, value))

            elif self._match(TokenType.COLON):
                self._validate_target(expr)
                self._advance()                         # consume `:`
                annotation = self._parse_annotation()
                value = None
                if self._match(TokenType.ASSIGN):
                    self._advance()
                    value = self._parse_expression()
                self._optional(TokenType.SEMICOLON)
                body.append(AnnotatedAssignmentNode(expr, annotation, value))

            elif self._match(TokenType.COMPOUND_ASSIGN):
                self._validate_target(expr)
                op = self._advance().lexeme
                value = self._parse_expression()
                self._optional(TokenType.SEMICOLON)
                body.append(CompoundAssignmentNode(expr, op, value))

            else:
                self._optional(TokenType.SEMICOLON)
                body.append(ExpressionNode(expr))

        self._expect(TokenType.RBRACE)
        class_decorators = list(decorators or [])
        if class_decorators:
            decorators.clear()
        return ClassDeclarationNode(name_tok.lexeme, bases, body, class_decorators)
    
    def _parse_param_list(self) -> list[Parameter]:
        """
        Parse the full comma-separated parameter list between ``(`` and ``)``.

        All five forms are handled here:

            name [: ann] [= default]   regular
            *name [: ann]              var-positional
            **name [: ann]             var-keyword
            /                          positional-only separator
            *                          keyword-only separator  (bare *, no name)
            **                         nameless var-keyword    (emits **_ in Python)

        Validation
        ----------
        - ``/`` must precede any ``*`` or ``**``.
        - At most one ``/``, one ``*``-family marker, one ``**``-family param.
        - No regular or ``*args`` parameters may follow ``**``.
        """
        params:   list[Parameter] = []
        seen_slash   = False
        seen_star    = False        # bare * or *args
        seen_kwargs  = False

        if self._match(TokenType.RPAREN):
            return params

        while True:
            tok = self._current

            # ── / ── positional-only separator ───────────────────────────────
            if self._is_op("/"):
                if seen_slash:
                    raise ParseError("Only one '/' separator is allowed in a parameter list")
                if seen_star or seen_kwargs:
                    raise ParseError("'/' must come before '*' and '**'")
                self._advance()
                params.append(Parameter(name="", kind="positional_sep"))
                seen_slash = True

            # ── * ── either *name or bare * (keyword-only separator) ──────────
            elif self._is_op("*"):
                if seen_star or seen_kwargs:
                    raise ParseError("Only one '*' or '*name' is allowed in a parameter list")
                self._advance()

                # bare *  — next meaningful token is , or )
                if self._current and self._current.token_type in {
                    TokenType.COMMA, TokenType.RPAREN
                }:
                    params.append(Parameter(name="", kind="keyword_sep"))
                else:
                    name = self._expect(TokenType.IDENTIFIER).lexeme
                    ann  = self._parse_inline_annotation()
                    params.append(Parameter(name=name, kind="args", annotation=ann))

                seen_star = True

            # ── ** ── either **name or bare ** (nameless kwargs → **_) ────────
            elif self._is_op("**"):
                if seen_kwargs:
                    raise ParseError("Only one '**' parameter is allowed in a parameter list")
                self._advance()

                # bare **  — next meaningful token is , or )
                if self._current and self._current.token_type in {
                    TokenType.COMMA, TokenType.RPAREN
                }:
                    params.append(Parameter(name="_", kind="kwargs"))
                else:
                    name = self._expect(TokenType.IDENTIFIER).lexeme
                    ann  = self._parse_inline_annotation()
                    params.append(Parameter(name=name, kind="kwargs", annotation=ann))

                seen_kwargs = True

            # ── regular parameter ─────────────────────────────────────────────
            else:
                if seen_kwargs:
                    raise ParseError(
                        "Regular parameters cannot follow '**'"
                    )
                params.append(self._parse_parameter())

            # ── advance past comma ─────────────────────────────────────────────
            if not self._match(TokenType.COMMA):
                break
            self._advance()
            if self._match(TokenType.RPAREN):
                break                               # trailing comma is fine

        return params


    def _is_op(self, lexeme: str) -> bool:
        """Return True if the current token is an OPERATOR with the given lexeme."""
        tok = self._current
        return (
            tok is not None
            and tok.token_type == TokenType.OPERATOR
            and tok.lexeme == lexeme
        )


    def _parse_inline_annotation(self) -> Expression | None:
        """Consume ``: annotation`` if present, else return None."""
        if self._match(TokenType.COLON):
            self._advance()
            return self._parse_annotation()
        return None


    def _parse_parameter(self) -> Parameter:
        """
        Parse a single regular parameter:
            name [: annotation] [= default]

        ``*``, ``**``, ``/`` are handled by ``_parse_param_list`` before
        this method is ever called.
        """
        name = self._expect(TokenType.IDENTIFIER).lexeme
        annotation = self._parse_inline_annotation()
        default = None
        if self._match(TokenType.ASSIGN):
            self._advance()
            default = self._parse_expression()
        return Parameter(name, default, "regular", annotation)
    
    def _parse_function_declaration(self, decorators: list[str] | None = None) -> FunctionDeclarationNode:
        """``function name ( params ) block``"""
        self._advance()                               # consume `function`
        name_tok = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.LPAREN)

        params = self._parse_param_list()

        self._expect(TokenType.RPAREN)

        return_type: Expression | None = None
        if self._match(TokenType.ARROW):
            self._advance()
            return_type = self._parse_annotation()

        body = self._parse_block()

        function_decorators = list(decorators or [])
        if function_decorators:
            decorators.clear()
        return FunctionDeclarationNode(
            name_tok.lexeme, params, body, function_decorators, return_type
        )
    
    def _parse_parameter(self) -> Parameter:
        """Parses one of: ``name``, ``name=expr``, ``*name``, ``**name``."""
        kind = "regular"

        if self._match(TokenType.OPERATOR):
            if self._current.lexeme == "**":
                self._advance(); kind = "kwargs"
            elif self._current.lexeme == "*":
                self._advance(); kind = "args"

        name = self._expect(TokenType.IDENTIFIER).lexeme

        annotation: Expression | None = None
        if self._match(TokenType.COLON):
            self._advance()
            annotation = self._parse_annotation()

        default: Expression | None = None
        if kind == "regular" and self._match(TokenType.ASSIGN):
            self._advance()
            default = self._parse_expression()

        return Parameter(name, default, kind, annotation)

    def _parse_return(self) -> ReturnNode:
        """``return [expr] ;``"""
        self._advance()                             # consume `return`

        # Bare return: next token is `;`, `}`, or EOF.
        if self._current is None or self._current.token_type in {
            TokenType.SEMICOLON,
            TokenType.RBRACE,
            TokenType.EOF,
        }:
            self._optional(TokenType.SEMICOLON)
            return ReturnNode(None)

        value = self._parse_expression()
        self._optional(TokenType.SEMICOLON)
        return ReturnNode(value)
    
    def _parse_raise(self) -> RaiseNode:
        """``raise [expr] ;``"""
        self._advance()                             # consume `raise`

        # Bare raise: next token is `;`, `}`, or EOF.
        if self._current is None or self._current.token_type in {
            TokenType.SEMICOLON,
            TokenType.RBRACE,
            TokenType.EOF,
        }:
            self._optional(TokenType.SEMICOLON)
            return ReturnNode(None)

        error = self._parse_expression()
        self._optional(TokenType.SEMICOLON)
        return RaiseNode(error)

    def _parse_block(self) -> BlockNode:
        """``{ statement* }``"""
        self._expect(TokenType.LBRACE)
        body: list[Node] = []
        while self._current and not self._match(TokenType.RBRACE):
            body.append(self._parse_statement())
        self._expect(TokenType.RBRACE)
        return BlockNode(body)
    

    # ── imports ──────────────────────────────────────────────────────────────────

    def _parse_module_name(self) -> str:
        """Dotted module name: ``os``, ``os.path``, etc."""
        parts = [self._expect(TokenType.IDENTIFIER).lexeme]
        while self._match(TokenType.DOT):
            self._advance()
            parts.append(self._expect(TokenType.IDENTIFIER).lexeme)
        return ".".join(parts)


    def _parse_import(self) -> ImportNode:
        """``import module [as alias]``"""
        self._advance()                                 # consume `import`
        module = self._parse_module_name()
        alias = None
        if self._match_keyword("as"):
            self._advance()
            alias = self._expect(TokenType.IDENTIFIER).lexeme
        self._optional(TokenType.SEMICOLON)
        return ImportNode(module, alias)


    def _parse_from_import(self) -> FromImportNode:
        """``from module import name [as alias], ...`` or ``from module import *``"""
        self._advance()                                 # consume `from`
        module = self._parse_module_name()

        if not self._match_keyword("import"):
            raise ParseError("Expected 'import' after module name",
                            self._current.row if self._current else None,
                            self._current.column if self._current else None)
        self._advance()                                 # consume `import`

        # star import
        if self._match(TokenType.OPERATOR) and self._current.lexeme == "*":
            self._advance()
            self._optional(TokenType.SEMICOLON)
            return FromImportNode(module, [("*", None)])

        names: list[tuple[str, str | None]] = [self._parse_import_alias()]
        while self._match(TokenType.COMMA):
            self._advance()
            names.append(self._parse_import_alias())

        self._optional(TokenType.SEMICOLON)
        return FromImportNode(module, names)


    def _parse_import_alias(self) -> tuple[str, str | None]:
        name = self._expect(TokenType.IDENTIFIER).lexeme
        alias = None
        if self._match_keyword("as"):
            self._advance()
            alias = self._expect(TokenType.IDENTIFIER).lexeme
        return (name, alias)


    # ── control flow ─────────────────────────────────────────────────────────────

    def _parse_if(self) -> IfNode:
        """``if cond { } [elif cond { }]* [else { }]``"""
        self._advance()                                 # consume `if`
        condition = self._parse_expression()
        body = self._parse_block()

        elifs: list[tuple[Expression, BlockNode]] = []
        while self._match_keyword("elif"):
            self._advance()
            elifs.append((self._parse_expression(), self._parse_block()))

        else_body = None
        if self._match_keyword("else"):
            self._advance()
            else_body = self._parse_block()

        return IfNode(condition, body, elifs, else_body)


    def _parse_for(self) -> ForNode:
        """``for target in iterable { } [else { }]``"""
        self._advance()                                 # consume `for`
        target = self._parse_for_target()

        if not self._match_keyword("in"):
            raise ParseError("Expected 'in' in for-loop",
                            self._current.row if self._current else None,
                            self._current.column if self._current else None)
        self._advance()                                 # consume `in`
        iterable = self._parse_expression()
        body = self._parse_block()

        else_body = None
        if self._match_keyword("else"):
            self._advance()
            else_body = self._parse_block()

        return ForNode(target, iterable, body, else_body)


    def _parse_for_target(self) -> str | list[str]:
        """
        Single identifier or parenthesised tuple: ``x`` or ``(x, y)``.
        """
        parens = self._match(TokenType.LPAREN)
        if parens:
            self._advance()

        names = [self._expect(TokenType.IDENTIFIER).lexeme]
        while self._match(TokenType.COMMA):
            self._advance()
            names.append(self._expect(TokenType.IDENTIFIER).lexeme)

        if parens:
            self._expect(TokenType.RPAREN)

        return names[0] if len(names) == 1 else names


    def _parse_while(self) -> WhileNode:
        """``while cond { } [else { }]``"""
        self._advance()                                 # consume `while`
        condition = self._parse_expression()
        body = self._parse_block()

        else_body = None
        if self._match_keyword("else"):
            self._advance()
            else_body = self._parse_block()

        return WhileNode(condition, body, else_body)


    # ── exception handling ────────────────────────────────────────────────────────

    def _parse_try(self) -> TryNode:
        """``try { } [except [T [as e]] { }]* [else { }] [finally { }]``"""
        self._advance()                                 # consume `try`
        body = self._parse_block()

        handlers: list[ExceptHandler] = []
        while self._match_keyword("except"):
            handlers.append(self._parse_except_handler())

        else_body = None
        if self._match_keyword("else"):
            self._advance()
            else_body = self._parse_block()

        finally_body = None
        if self._match_keyword("finally"):
            self._advance()
            finally_body = self._parse_block()

        if not handlers and finally_body is None:
            raise ParseError("'try' requires at least one 'except' or 'finally'")

        return TryNode(body, handlers, else_body, finally_body)


    def _parse_except_handler(self) -> ExceptHandler:
        """
        ``except { }``
        ``except TypeError { }``
        ``except (TypeError, ValueError) { }``
        ``except TypeError as e { }``
        """
        self._advance()                                 # consume `except`

        exceptions: list[str] = []
        alias: str | None = None

        if not self._match(TokenType.LBRACE):           # not a bare except
            if self._match(TokenType.LPAREN):           # tuple of types
                self._advance()
                exceptions.append(self._expect(TokenType.IDENTIFIER).lexeme)
                while self._match(TokenType.COMMA):
                    self._advance()
                    exceptions.append(self._expect(TokenType.IDENTIFIER).lexeme)
                self._expect(TokenType.RPAREN)
            else:
                exceptions.append(self._expect(TokenType.IDENTIFIER).lexeme)

            if self._match_keyword("as"):
                self._advance()
                alias = self._expect(TokenType.IDENTIFIER).lexeme

        return ExceptHandler(exceptions, alias, self._parse_block())
    

    # ── other ─────────────────────────────────────────────────────────────────────

    def _parse_annotation(self) -> Expression:
        """
        Parse a type annotation as a postfix expression.
        Handles ``int``, ``list[int]``, ``dict[str, int]`` etc.
        Stops before binary operators so ``x: int = 5`` parses correctly.
        """
        return self._parse_postfix()


    def _parse_unpackable(self) -> Expression:
        """
        Parse a possibly-starred element for tuples, arrays, and
        destructuring patterns: ``*name`` or any expression.
        """
        if self._match(TokenType.OPERATOR) and self._current.lexeme == "*":
            self._advance()
            name = self._expect(TokenType.IDENTIFIER).lexeme
            return StarExpression(name)
        return self._parse_expression()
    

    def _split_fstring_placeholder(
        self, content: str
    ) -> tuple[str, str | None, str | None]:
        """
        Split the raw content of a ``{...}`` placeholder into
        ``(expr_src, conversion, format_spec)``.

        Examples
        --------
        ``"x"``         → ``("x",   None, None)``
        ``"x!r"``       → ``("x",   "r",  None)``
        ``"x:.2f"``     → ``("x",   None, ".2f")``
        ``"x!r:.2f"``   → ``("x",   "r",  ".2f")``
        ``"d[k]:.4e"``  → ``("d[k]",None, ".4e")``

        Nesting is tracked so that ``{x:{w}.{p}}`` does not split on the
        inner colons.
        """
        depth = 0
        for i, ch in enumerate(content):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif depth == 0:
                if ch == "!":
                    expr_src = content[:i].strip()
                    rest     = content[i + 1:]
                    if rest and rest[0] in "rsa":
                        conversion  = rest[0]
                        format_spec = rest[2:] if rest[1:].startswith(":") else None
                        return expr_src, conversion, format_spec or None
                    # bare `!` not followed by a valid flag — treat as expression
                    return content.strip(), None, None
                if ch == ":":
                    expr_src    = content[:i].strip()
                    format_spec = content[i + 1:]
                    return expr_src, None, format_spec or None
        return content.strip(), None, None


    def _parse_fstring_content(
        self, raw: str, prefix: str = "f"
    ) -> FStringExpression:
        """
        Walk the raw f-string lexeme, split on ``{...}`` placeholders, parse
        each inner expression via a sub-parser, and collect conversion flags
        and format specs.
        """

        parts: list[str | FStringPart] = []
        buf   = ""
        i     = 0

        while i < len(raw):
            ch = raw[i]

            if ch == "{":
                if i + 1 < len(raw) and raw[i + 1] == "{":   # escaped {{
                    buf += "{"
                    i   += 2
                    continue
                if buf:
                    parts.append(buf)
                    buf = ""
                # locate the matching closing brace, respecting nesting
                depth, j = 1, i + 1
                while j < len(raw) and depth > 0:
                    if   raw[j] == "{": depth += 1
                    elif raw[j] == "}": depth -= 1
                    j += 1
                placeholder                   = raw[i + 1 : j - 1]
                expr_src, conversion, fmt_spec = self._split_fstring_placeholder(placeholder)
                sub  = Parser(Lexer(expr_src, rules=self._lexer.rules)).load()
                expr = sub._parse_expression()
                parts.append(FStringPart(expr, conversion, fmt_spec))
                i = j

            elif ch == "}" and i + 1 < len(raw) and raw[i + 1] == "}":  # escaped }}
                buf += "}"
                i   += 2

            else:
                buf += ch
                i   += 1

        if buf:
            parts.append(buf)

        return FStringExpression(parts, prefix)


    def _parse_with(self) -> WithNode:
        """``with ctx [as name], ... { }``"""
        self._advance()                                 # consume 'with'
        items = [self._parse_with_item()]
        while self._match(TokenType.COMMA):
            self._advance()
            items.append(self._parse_with_item())
        return WithNode(items, self._parse_block())


    def _parse_with_item(self) -> WithItem:
        context = self._parse_expression()
        alias = None
        if self._match_keyword("as"):
            self._advance()
            alias = self._expect(TokenType.IDENTIFIER).lexeme
        return WithItem(context, alias)


    def _parse_assert(self) -> AssertNode:
        """``assert condition [, message]``"""
        self._advance()                                 # consume 'assert'
        condition = self._parse_expression()
        message = None
        if self._match(TokenType.COMMA):
            self._advance()
            message = self._parse_expression()
        self._optional(TokenType.SEMICOLON)
        return AssertNode(condition, message)
    
    def _parse_case_patterns(self) -> Pattern:
        """
        Parse one or more comma-separated patterns.
        Multiple patterns become an ``OrPattern``.
        """
        first = self._parse_pattern()
        if not self._match(TokenType.COMMA):
            return first
        patterns = [first]
        while self._match(TokenType.COMMA):
            self._advance()
            patterns.append(self._parse_pattern())
        return OrPattern(patterns)


    def _parse_pattern(self) -> Pattern:
        """
        Parse a single atomic pattern.

        Forms supported
        ---------------
        ``_``                  Wildcard — matches anything.
        ``1``, ``"s"``         Literal — matches that exact constant.
        ``-1``, ``-3.14``      Negative numeric literal.
        ``true`` / ``false``   Boolean literals.
        ``null``               None literal.
        ``name``               Capture — binds the value to a new variable.
        ``Enum.MEMBER``        Value pattern — dotted qualified name.
        """
        tok = self._current
        if tok is None:
            raise ParseError("Unexpected end of input while parsing pattern")

        # ── wildcard ──────────────────────────────────────────────────────────
        if tok.token_type == TokenType.IDENTIFIER and tok.lexeme == "_":
            self._advance()
            return WildcardPattern()

        # ── boolean / null pseudo-literals ────────────────────────────────────
        if tok.token_type == TokenType.IDENTIFIER and tok.lexeme in {"true", "false", "null"}:
            self._advance()
            py_val: bool | None = {"true": True, "false": False, "null": None}[tok.lexeme]
            return LiteralPattern(Literal(py_val))

        # ── numeric literal ───────────────────────────────────────────────────
        if tok.token_type == TokenType.NUMBER:
            self._advance()
            val = float(tok.lexeme) if "." in tok.lexeme else int(tok.lexeme)
            return LiteralPattern(Literal(val))

        # ── negative numeric literal: -1, -3.14 ──────────────────────────────
        if (
            tok.token_type == TokenType.OPERATOR and tok.lexeme == "-"
            and self._peek() is not None
            and self._peek().token_type == TokenType.NUMBER
        ):
            self._advance()                             # consume '-'
            num = self._advance()
            val = float(num.lexeme) if "." in num.lexeme else int(num.lexeme)
            return LiteralPattern(Literal(-val))

        # ── string literal ────────────────────────────────────────────────────
        if tok.token_type == TokenType.STRING:
            self._advance()
            return LiteralPattern(Literal(tok.lexeme, prefix=tok.prefix))

        # ── identifier: capture or qualified value ────────────────────────────
        if tok.token_type == TokenType.IDENTIFIER and tok.lexeme not in KEYWORDS:
            name = self._advance().lexeme

            # dotted name → value pattern (e.g. Status.OK)
            if self._match(TokenType.DOT):
                expr: Expression = Identifier(name)
                while self._match(TokenType.DOT):
                    self._advance()
                    member = self._expect(TokenType.IDENTIFIER).lexeme
                    expr   = MemberAccessExpression(expr, member)
                return ValuePattern(expr)

            # bare name → capture
            return CapturePattern(name)

        raise ParseError(
            f"Expected a pattern (literal, name, _, or Qualified.Name), "
            f"got {tok!r}",
            tok.row, tok.column,
        )
    
    def _parse_switch(self) -> SwitchNode:
        """``switch subject { case ... default ... }``"""
        self._advance()                                 # consume 'switch'
        subject = self._parse_expression()
        self._expect(TokenType.LBRACE)

        cases:        list[CaseClause] = []
        default_body: BlockNode | None = None

        while self._current and not self._match(TokenType.RBRACE):

            if self._match_keyword("case"):
                self._advance()                         # consume 'case'
                pattern = self._parse_case_patterns()

                guard = None
                if self._match_keyword("if"):
                    self._advance()                     # consume 'if'
                    guard = self._parse_expression()

                cases.append(CaseClause(pattern, guard, self._parse_block()))

            elif self._match_keyword("default"):
                self._advance()                         # consume 'default'
                if default_body is not None:
                    raise ParseError("A switch may only have one 'default' clause")
                default_body = self._parse_block()

            else:
                tok = self._current
                raise ParseError(
                    "Expected 'case' or 'default' inside switch body",
                    tok.row if tok else None,
                    tok.column if tok else None,
                )

        self._expect(TokenType.RBRACE)
        return SwitchNode(subject, cases, default_body)


    # ----------------------------------------------------------- expressions

    # Operator precedence table (higher number = tighter binding).
    PRECEDENCE: dict[str, int] = {
        "||": 1, "or":  1,
        "&&": 2, "and": 2,
        "==": 3, "!=":  3,
        "in": 4, "not in": 4, "is": 4, "is not": 4,
        "<":  4, ">":   4, "<=": 4, ">=": 4,
        "+":  5, "-":   5,
        "*":  6, "/":   6, "%":  6,
    }

    def _current_binary_op(self) -> str | None:
        """
        Return the operator string at the current position, or ``None``.
        Covers both symbol tokens and keyword operators, including the
        two-token forms ``not in`` and ``is not``.
        """
        tok = self._current
        if tok is None:
            return None
        if tok.token_type == TokenType.OPERATOR:
            return tok.lexeme
        if tok.token_type == TokenType.IDENTIFIER:
            nxt = self._peek()
            nxt_lex = nxt.lexeme if nxt and nxt.token_type == TokenType.IDENTIFIER else ""
            if tok.lexeme == "not" and nxt_lex == "in":
                return "not in"
            if tok.lexeme == "is" and nxt_lex == "not":
                return "is not"
            if tok.lexeme in {"in", "is", "and", "or"}:
                return tok.lexeme
        return None


    def _advance_binary_op(self, op: str) -> None:
        """Consume one or two tokens depending on the operator."""
        self._advance()
        if op in {"not in", "is not"}:
            self._advance()

    def _parse_expression(self, min_prec: int = 0) -> Expression:
        """Pratt-style binary expression parser."""
        left = self._parse_unary()

        while True:
            op = self._current_binary_op()
            if op is None:
                break
            prec = self.PRECEDENCE.get(op)
            if prec is None or prec < min_prec:
                break
            self._advance_binary_op(op)
            right = self._parse_expression(prec + 1)
            left = BinaryExpression(left, op, right)
        
        # ternary — lowest precedence, right-associative
        if min_prec == 0 and self._match(TokenType.QUESTION):
            self._advance()                             # consume ?
            consequent = self._parse_expression(0)
            self._expect(TokenType.COLON)
            alternate = self._parse_expression(0)
            return TernaryExpression(left, consequent, alternate)

        return left

    def _parse_unary(self) -> Expression:
        """Handles prefix unary operators: ``!``, ``-``."""
        if self._match(TokenType.OPERATOR) and self._current.lexeme in {"!", "-"}:
            op = self._advance().lexeme
            return UnaryExpression(op, self._parse_unary())

        if self._match_keyword("not"):          # ← new
            self._advance()
            return UnaryExpression("not", self._parse_unary())
    
        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        """
        Handles postfix chains: member access (``a.b``) and calls
        (``f(x)``), in any combination and nesting depth.
        """
        expr = self._parse_primary()

        while True:
            if self._match(TokenType.DOT):          # member access
                self._advance()
                member_tok = self._expect(TokenType.IDENTIFIER)
                expr = MemberAccessExpression(expr, member_tok.lexeme)

            elif self._match(TokenType.LPAREN):     # call
                expr = self._parse_call(expr)
            
            elif self._match(TokenType.LBRACKET):       # ← subscript
                self._advance()                         # consume `[`
                index = self._parse_expression()
                self._expect(TokenType.RBRACKET)
                expr = SubscriptExpression(expr, index)

            else:
                break

        return expr

    def _parse_primary(self) -> Expression:
        """Handles the atomic expression forms."""
        tok = self._current
        if tok is None or tok.token_type == TokenType.EOF:
            raise ParseError("Unexpected end of input")

        # numeric literal
        if tok.token_type == TokenType.NUMBER:
            self._advance()
            val: int | float = (
                float(tok.lexeme) if "." in tok.lexeme else int(tok.lexeme)
            )
            return Literal(val)

        # string literal
        if tok.token_type == TokenType.STRING:
            self._advance()
            return Literal(tok.lexeme, prefix=tok.prefix)   # ← prefix forwarded

        # f-string
        if tok.token_type == TokenType.FSTRING:
            self._advance()
            return self._parse_fstring_content(tok.lexeme, tok.prefix)   # ← prefix forwarded

        # identifier (variable reference)
        if tok.token_type == TokenType.IDENTIFIER:
            self._advance()
            return Identifier(tok.lexeme)

        # tuple / walrus / grouping
        if tok.token_type == TokenType.LPAREN:
            self._advance()

            # empty tuple: ()
            if self._match(TokenType.RPAREN):
                self._advance()
                return TupleExpression([])

            first = self._parse_unpackable()

            # tuple: (a, b, *rest, ...)
            if self._match(TokenType.COMMA):
                elements = [first]
                while self._match(TokenType.COMMA):
                    self._advance()
                    if self._match(TokenType.RPAREN):
                        break                               # trailing comma ok
                    elements.append(self._parse_unpackable())
                self._expect(TokenType.RPAREN)
                return TupleExpression(elements)

            # walrus: (name := expr)
            if isinstance(first, Identifier) and self._match(TokenType.WALRUS):
                self._advance()                             # consume :=
                value = self._parse_expression()
                self._expect(TokenType.RPAREN)
                return WalrusExpression(first.name, value)

            # plain grouping: (expr)
            self._expect(TokenType.RPAREN)
            return GroupExpression(first)

        # array literal: [ elem, ... ]
        if tok.token_type == TokenType.LBRACKET:
            return self._parse_array()

        if tok.token_type == TokenType.LBRACE:
            raise ParseError(
                "Unexpected '{' inside an expression — "
                "blocks are only valid as statements",
                tok.row,
                tok.column,
            )

        raise ParseError(
            f"Unexpected token {tok!r}",
            tok.row,
            tok.column,
        )

    def _parse_call(self, callee: Expression) -> CallExpression:
        """``callee ( arg, ... )``"""
        self._expect(TokenType.LPAREN)
        args: list[Argument] = []

        if not self._match(TokenType.RPAREN):
            args.append(self._parse_argument())
            while self._match(TokenType.COMMA):
                self._advance()
                args.append(self._parse_argument())

        self._expect(TokenType.RPAREN)
        return CallExpression(callee, args)
    
    def _parse_argument(self) -> Argument:
        """
        Parses one of:

        ``**expr``   →  kwargs  (must come last in a real call)
        ``*expr``    →  args
        ``name=expr``→  keyword
        ``expr``     →  regular positional
        """
        # **expr
        if self._match(TokenType.OPERATOR) and self._current.lexeme == "**":
            self._advance()
            return Argument(self._parse_expression(), kind="kwargs")

        # *expr
        if self._match(TokenType.OPERATOR) and self._current.lexeme == "*":
            self._advance()
            return Argument(self._parse_expression(), kind="args")

        # name=expr — one token of lookahead to distinguish from a regular expression
        if (
            self._match(TokenType.IDENTIFIER)
            and self._peek() is not None
            and self._peek().token_type == TokenType.ASSIGN
        ):
            keyword = self._advance().lexeme        # consume the name
            self._advance()                         # consume `=`
            return Argument(self._parse_expression(), keyword=keyword, kind="keyword")

        # plain positional
        return Argument(self._parse_expression(), kind="regular")

    def _parse_array(self) -> ArrayExpression:
        """``[ elem, ... ]``"""
        self._expect(TokenType.LBRACKET)
        elements: list[Expression] = []

        if not self._match(TokenType.RBRACKET):
            elements.append(self._parse_unpackable())
            while self._match(TokenType.COMMA):
                self._advance()
                elements.append(self._parse_unpackable())

        self._expect(TokenType.RBRACKET)
        return ArrayExpression(elements)