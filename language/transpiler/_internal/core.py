"""
transpiler/core.py
~~~~~~~~~~~~~~~~~~
Python code generator / transpiler.

The :class:`PythonTranspiler` converts the AST produced by
:class:`~parser.core.Parser` into a Python source string.

Improvements over the original
-------------------------------
* ``FunctionDeclarationNode`` is handled directly — no more fragile
  heuristic that stitched ``function`` + ``foo(x)`` + ``BlockNode``
  together across three consecutive generator iterations.

* ``ReturnNode`` is emitted as a proper ``return`` statement.

* ``UnaryExpression`` and ``MemberAccessExpression`` are evaluated
  correctly.

* ``_eval`` raises ``TypeError`` on unrecognised expression types
  rather than silently returning ``None``.

* The public entry point is :meth:`transpile`, which returns the
  complete Python source as a single string.
"""

from __future__ import annotations

from ...lexer.core import Lexer
from ...lexer.rules import DEFAULT_RULES, Rule
from ...parser.core import Parser
from ...parser.nodes import (
    Parameter,
    Decorator,
    ArrayExpression,
    AssignmentNode,
    CompoundAssignmentNode,
    AnnotatedAssignmentNode,
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
    TryNode,
    BreakNode,
    ContinueNode,
    PassNode
)

# Default token-level identifier translations, applied when evaluating
# an ``Identifier`` expression node.
DEFAULT_TRANSLATIONS: dict[str, str] = {
    "true":  "True",
    "false": "False",
    "null":  "None",
}

DEFAULT_DECORATOR_TRANSLATIONS: dict[str, str] = {
    "static":   "staticmethod",
    "abstract": "abstractmethod",
    "class": "classmethod",
}


class PythonTranspiler:
    """
    Converts source text (or any :data:`~lexer.source.SourceLike` input)
    into Python source code.

    Parameters
    ----------
    data:
        The source to transpile.
    rules:
        Lexer rules to use. Defaults to
        :data:`~lexer.rules.DEFAULT_RULES`.
    translations:
        A mapping of identifier strings to their Python equivalents.
        Merged on top of :data:`DEFAULT_TRANSLATIONS`; pass an empty
        dict to disable defaults.

    Usage
    -----
    ::

        src = '''
            function greet(name) {
                print("Hello, " + name);
            }
            greet("World");
        '''
        code = PythonTranspiler(src).load().transpile()
        print(code)
    """

    __slots__ = (
        "_parser",
        "nodes",
        "_translations",
        "_decorator_translations"
    )

    def __init__(
        self,
        data,
        *,
        rules: list[Rule] | None = None,
        translations: dict[str, str] | None = None,
        decorator_translations: dict[str, str] | None = None,
    ) -> None:
        effective_rules = rules if rules is not None else DEFAULT_RULES
        lexer = Lexer(data, rules=effective_rules)
        self._parser = Parser(lexer)
        self.nodes: list[Node] = []
        self._translations: dict[str, str] = {
            **DEFAULT_TRANSLATIONS,
            **(translations or {}),
        }
        self._decorator_translations: dict[str, str] = {
            **DEFAULT_DECORATOR_TRANSLATIONS,
            **(decorator_translations or {}),
        }

    # ------------------------------------------------------------------ setup

    def load(self) -> "PythonTranspiler":
        """
        Lex and parse the source.
        Returns ``self`` to allow method chaining.
        """
        self._parser.load()
        self.nodes = self._parser.parse()
        return self

    # ------------------------------------------------------------ public API

    def transpile(self) -> str:
        """Return the full Python source as a single string."""
        return "\n".join(self._generate(self.nodes, indent=0))

    # --------------------------------------------------------- code generator

    _INDENT = "    "        # four spaces per indent level

    def _generate(self, nodes: list[Node], indent: int) -> list[str]:
        """Recursively emit Python lines for a list of AST nodes."""
        lines: list[str] = []
        pad = self._INDENT * indent

        for node in nodes:

            # ── function declaration ───────────────────────────────────────
            if isinstance(node, FunctionDeclarationNode):
                for dec in node.decorators:
                    lines.append(self._emit_decorator(dec, pad))
                ret = f" -> {self._eval(node.return_type)}" if node.return_type else ""
                lines.append(f"{pad}def {node.name}({self._emit_params(node.params)}){ret}:")
                body_lines = self._generate(node.body.body, indent + 1)
                lines.extend(body_lines if body_lines else [f"{pad}    pass"])
            
            elif isinstance(node, ClassDeclarationNode):
                for dec in node.decorators:
                    lines.append(self._emit_decorator(dec, pad))
                base = f"({', '.join(node.bases)})" if node.bases else ""
                lines.append(f"{pad}class {node.name}{base}:")

                if not node.methods:
                    lines.append(f"{pad}{self._INDENT}pass")
                else:
                    # methods — inject_self=True, and pass method decorators too
                    for method in node.methods:
                        is_static = False
                        for dec in method.decorators:
                            dec = self._decorator_translations.get(dec, dec)
                            lines.append(self._emit_decorator(dec, pad))
                            if dec == "staticmethod":
                                is_static = True
                        lines.append(f"{pad}{self._INDENT}def {method.name}({self._emit_params(method.params, inject_self=not is_static)}):")
                        body_lines = self._generate(method.body.body, indent + 2)
                        lines.extend(body_lines if body_lines else [f"{pad}{self._INDENT * 2}pass"])

            # ── return statement ───────────────────────────────────────────
            elif isinstance(node, ReturnNode):
                if node.value is None:
                    lines.append(f"{pad}return")
                else:
                    lines.append(f"{pad}return {self._eval(node.value)}")
            
            elif isinstance(node, RaiseNode):
                if node.error is None:
                    lines.append(f"{pad}raise")
                else:
                    lines.append(f"{pad}raise {self._eval(node.error)}")

            # ── variable assignment ────────────────────────────────────────
            elif isinstance(node, AssignmentNode):
                lines.append(
                    f"{pad}{self._eval(node.target)} = {self._eval(node.value)}"
                )

            elif isinstance(node, CompoundAssignmentNode):
                lines.append(
                    f"{pad}{self._eval(node.target)} {node.operator} {self._eval(node.value)}"
                )
            
            elif isinstance(node, AnnotatedAssignmentNode):
                target = self._eval(node.target)
                ann    = self._eval(node.annotation)
                if node.value is not None:
                    lines.append(f"{pad}{target}: {ann} = {self._eval(node.value)}")
                else:
                    lines.append(f"{pad}{target}: {ann}")

            elif isinstance(node, WithNode):
                parts = [
                    f"{self._eval(i.context)} as {i.alias}" if i.alias
                    else self._eval(i.context)
                    for i in node.items
                ]
                lines.append(f"{pad}with {', '.join(parts)}:")
                lines.extend(self._generate(node.body.body, indent + 1) or [f"{pad}    pass"])

            elif isinstance(node, AssertNode):
                cond = self._eval(node.condition)
                if node.message:
                    lines.append(f"{pad}assert {cond}, {self._eval(node.message)}")
                else:
                    lines.append(f"{pad}assert {cond}")

            # ── standalone block (rare but legal) ─────────────────────────
            elif isinstance(node, BlockNode):
                lines.extend(self._generate(node.body, indent + 1))

            # ── expression statement ───────────────────────────────────────
            elif isinstance(node, ExpressionNode):
                lines.append(f"{pad}{self._eval(node.expr)}")
        
            # ── imports ──────────────────────────────────────────────────────────────────

            elif isinstance(node, ImportNode):
                suffix = f" as {node.alias}" if node.alias else ""
                lines.append(f"{pad}import {node.module}{suffix}")

            elif isinstance(node, FromImportNode):
                parts = [
                    f"{name} as {alias}" if alias else name
                    for name, alias in node.names
                ]
                lines.append(f"{pad}from {node.module} import {', '.join(parts)}")

            # ── control flow ─────────────────────────────────────────────────────────────

            elif isinstance(node, IfNode):
                lines.append(f"{pad}if {self._eval(node.condition)}:")
                lines.extend(self._generate(node.body.body, indent + 1) or [f"{pad}    pass"])
                for cond, block in node.elifs:
                    lines.append(f"{pad}elif {self._eval(cond)}:")
                    lines.extend(self._generate(block.body, indent + 1) or [f"{pad}    pass"])
                if node.else_body is not None:
                    lines.append(f"{pad}else:")
                    lines.extend(self._generate(node.else_body.body, indent + 1) or [f"{pad}    pass"])

            elif isinstance(node, ForNode):
                target = ", ".join(node.target) if isinstance(node.target, list) else node.target
                lines.append(f"{pad}for {target} in {self._eval(node.iterable)}:")
                lines.extend(self._generate(node.body.body, indent + 1) or [f"{pad}    pass"])
                if node.else_body is not None:
                    lines.append(f"{pad}else:")
                    lines.extend(self._generate(node.else_body.body, indent + 1) or [f"{pad}    pass"])

            elif isinstance(node, WhileNode):
                lines.append(f"{pad}while {self._eval(node.condition)}:")
                lines.extend(self._generate(node.body.body, indent + 1) or [f"{pad}    pass"])
                if node.else_body is not None:
                    lines.append(f"{pad}else:")
                    lines.extend(self._generate(node.else_body.body, indent + 1) or [f"{pad}    pass"])

            elif isinstance(node, TryNode):
                lines.append(f"{pad}try:")
                lines.extend(self._generate(node.body.body, indent + 1) or [f"{pad}    pass"])
                for h in node.handlers:
                    if not h.exceptions:
                        lines.append(f"{pad}except:")
                    elif len(h.exceptions) == 1:
                        exc = h.exceptions[0]
                        suffix = f" as {h.alias}" if h.alias else ""
                        lines.append(f"{pad}except {exc}{suffix}:")
                    else:
                        excs = f"({', '.join(h.exceptions)})"
                        suffix = f" as {h.alias}" if h.alias else ""
                        lines.append(f"{pad}except {excs}{suffix}:")
                    lines.extend(self._generate(h.body.body, indent + 1) or [f"{pad}    pass"])
                if node.else_body is not None:
                    lines.append(f"{pad}else:")
                    lines.extend(self._generate(node.else_body.body, indent + 1) or [f"{pad}    pass"])
                if node.finally_body is not None:
                    lines.append(f"{pad}finally:")
                    lines.extend(self._generate(node.finally_body.body, indent + 1) or [f"{pad}    pass"])

            # ── loop control / no-op ─────────────────────────────────────────────────────

            elif isinstance(node, BreakNode):    lines.append(f"{pad}break")
            elif isinstance(node, ContinueNode): lines.append(f"{pad}continue")
            elif isinstance(node, PassNode):     lines.append(f"{pad}pass")

        return lines

    # --------------------------------------------------------- expression eval

    def _eval(self, expr: Expression) -> str:
        """Recursively lower an expression node to a Python string."""

        if isinstance(expr, Literal):
            if isinstance(expr.value, str):
                # Re-quote the string; the lexer strips the quotes.
                escaped = expr.value.replace("\\", "\\\\").replace('"', '\\"')
                return f'"{escaped}"'
            # Integers are emitted without a decimal point.
            if isinstance(expr.value, int):
                return str(expr.value)
            # Floats: strip trailing zeros for tidiness (3.0 → "3.0" kept).
            return str(expr.value)

        if isinstance(expr, Identifier):
            return self._translations.get(expr.name, expr.name)

        if isinstance(expr, UnaryExpression):
            op = "not " if expr.operator in {"!", "not"} else expr.operator
            return f"{op}{self._eval(expr.operand)}"

        if isinstance(expr, BinaryExpression):
            op = {"&&": "and", "||": "or"}.get(expr.operator, expr.operator)
            # `in`, `not in`, `is`, `is not`, `and`, `or` pass through unchanged
            return f"({self._eval(expr.left)} {op} {self._eval(expr.right)})"

        if isinstance(expr, MemberAccessExpression):
            return f"{self._eval(expr.obj)}.{expr.member}"

        if isinstance(expr, CallExpression):
            callee = self._eval(expr.callee)
            parts: list[str] = []

            for arg in expr.args:
                if arg.kind == "args":
                    parts.append(f"*{self._eval(arg.value)}")
                elif arg.kind == "kwargs":
                    parts.append(f"**{self._eval(arg.value)}")
                elif arg.kind == "keyword":
                    parts.append(f"{arg.keyword}={self._eval(arg.value)}")
                else:
                    parts.append(self._eval(arg.value))

            return f"{callee}({', '.join(parts)})"
        
        if isinstance(expr, SubscriptExpression):
            return f"{self._eval(expr.obj)}[{self._eval(expr.index)}]"

        if isinstance(expr, ArrayExpression):
            elements = ", ".join(self._eval(e) for e in expr.elements)
            return f"[{elements}]"
        
        if isinstance(expr, TupleExpression):
            if not expr.elements:
                return "()"
            parts = [
                f"*{e.name}" if isinstance(e, StarExpression) else self._eval(e)
                for e in expr.elements
            ]
            # single-element tuple needs a trailing comma
            if len(parts) == 1 and not isinstance(expr.elements[0], StarExpression):
                return f"({parts[0]},)"
            return f"({', '.join(parts)})"

        if isinstance(expr, StarExpression):
            return f"*{expr.name}"

        if isinstance(expr, FStringExpression):
            body = "".join(
                part.replace("{", "{{").replace("}", "}}")
                if isinstance(part, str)
                else f"{{{self._eval(part)}}}"
                for part in expr.parts
            )
            return f'f"{body}"'

        if isinstance(expr, TernaryExpression):
            # C:   cond ? x : y
            # Py:  x if cond else y
            return (
                f"({self._eval(expr.consequent)} "
                f"if {self._eval(expr.condition)} "
                f"else {self._eval(expr.alternate)})"
            )

        if isinstance(expr, WalrusExpression):
            return f"({expr.target} := {self._eval(expr.value)})"

        if isinstance(expr, GroupExpression):
            return f"({self._eval(expr.expression)})"

        raise TypeError(
            f"Cannot evaluate unknown expression type: "
            f"{type(expr).__name__!r}"
        )
    
    # ------------------------------------------------------------- emit params

    def _emit_param(self, p: Parameter) -> str:
        annotation = f": {self._eval(p.annotation)}" if p.annotation else ""
        if p.kind == "args":
            return f"*{p.name}{annotation}"
        if p.kind == "kwargs":
            return f"**{p.name}{annotation}"
        if p.default is not None:
            return f"{p.name}{annotation}={self._eval(p.default)}"
        return f"{p.name}{annotation}"


    def _emit_params(self, params: list[Parameter], inject_self: bool = False) -> str:
        parts = ["self"] if inject_self else []
        for p in params:
            if p.name == "self":
                continue
            parts.append(self._emit_param(p))
        return ", ".join(parts)
    
    def _emit_decorator(self, dec: Decorator, pad: str) -> str:
        if isinstance(dec.expr, Identifier):
            name = self._decorator_translations.get(dec.expr.name, dec.expr.name)
            return f"{pad}@{name}"
        return f"{pad}@{self._eval(dec.expr)}"