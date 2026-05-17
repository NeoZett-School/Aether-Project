"""
parser/nodes.py
~~~~~~~~~~~~~~~
Abstract Syntax Tree (AST) node definitions.

Expressions
-----------
``Literal``               A numeric, string, or boolean constant.
``Identifier``            A name reference.
``UnaryExpression``       One operator applied to one operand  (``!x``, ``-x``).
``BinaryExpression``      Two operands joined by an operator  (``a + b``).
``MemberAccessExpression``  Dot-notation member access  (``obj.field``).
``CallExpression``        A callable invoked with arguments  (``f(x, y)``).
``ArrayExpression``       An array literal  (``[1, 2, 3]``).
``GroupExpression``       A parenthesised sub-expression  (``(a + b)``).

Statements
----------
``ExpressionNode``          A bare expression used as a statement.
``AssignmentNode``          Variable binding: ``name = expr``.
``BlockNode``               A ``{ ... }`` sequence of statements.
``FunctionDeclarationNode`` A named function with parameters and a body.
``ReturnNode``              A ``return`` statement (value optional).
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Union, Literal as _Literal

ParameterKind = _Literal["regular", "args", "kwargs"]
ArgumentKind = _Literal["regular", "keyword", "args", "kwargs"]


@dataclass(slots=True)
class Parameter:
    """
    A single function parameter.

    Attributes
    ----------
    name:     The parameter identifier.
    default:  Default-value expression, or ``None``.
    kind:     ``"regular"``, ``"args"`` (``*``), or ``"kwargs"`` (``**``).
    """
    name: str
    default: Expression | None = None
    kind: ParameterKind = "regular"
    annotation: Expression | None = None


@dataclass(slots=True)
class Argument:
    """
    A single call-site argument.

    Attributes
    ----------
    value:   The expression being passed.
    keyword: The parameter name, only set when ``kind == "keyword"``.
    kind:    ``"regular"``, ``"keyword"``, ``"args"`` (``*``), or ``"kwargs"`` (``**``).
    """
    value: Expression
    keyword: str | None = None
    kind: ArgumentKind = "regular"


@dataclass(slots=True)
class Decorator:
    """
    A decorator applied to a function or class.

    ``expr`` may be any postfix expression:
      - bare identifier:    ``@staticmethod``
      - member access:      ``@app.route``
      - call:               ``@app.route("/")``
      - chained call:       ``@pytest.mark.parametrize("x", [1, 2])``
    """
    expr: Expression

# ---------------------------------------------------------------------------
# Expression hierarchy
# ---------------------------------------------------------------------------


class Expression(ABC):
    """Marker base for all expression nodes."""


@dataclass(slots=True)
class Literal(Expression):
    """A literal value: integer, float, or string."""
    value: Union[int, float, str]
    prefix: str = ""


@dataclass(slots=True)
class Identifier(Expression):
    """A named reference (variable, keyword, etc.)."""
    name: str


@dataclass(slots=True)
class UnaryExpression(Expression):
    """
    A prefix unary expression, e.g. ``!flag`` or ``-x``.

    Attributes
    ----------
    operator:
        The operator character(s), e.g. ``"!"`` or ``"-"``.
    operand:
        The expression the operator is applied to.
    """
    operator: str
    operand: Expression


@dataclass(slots=True)
class BinaryExpression(Expression):
    """
    An infix binary expression, e.g. ``a + b``.

    Attributes
    ----------
    left, right:
        The two sub-expressions.
    operator:
        The operator string, e.g. ``"+"`` or ``"=="`` .
    """
    left: Expression
    operator: str
    right: Expression


@dataclass(slots=True)
class MemberAccessExpression(Expression):
    """
    Dot-notation member access, e.g. ``obj.field``.

    Chains naturally: ``a.b.c`` becomes
    ``MemberAccess(MemberAccess(a, "b"), "c")``.
    """
    obj: Expression
    member: str


@dataclass(slots=True)
class CallExpression(Expression):
    """
    A function / method call, e.g. ``f(x, y)``.

    Attributes
    ----------
    callee:
        The expression that resolves to the callable.
    args:
        Positional arguments.
    """
    callee: Expression
    args: list[Argument] = field(default_factory=list)


@dataclass(slots=True)
class SubscriptExpression(Expression):
    """
    Index / key / item access: ``obj[index]``.

    Attributes
    ----------
    obj:   The expression being subscripted.
    index: The index or key expression inside the brackets.
    """
    obj: Expression
    index: Expression


@dataclass(slots=True)
class ArrayExpression(Expression):
    """An array literal, e.g. ``[1, 2, 3]``."""
    elements: list[Expression] = field(default_factory=list)


@dataclass(slots=True)
class TupleExpression(Expression):
    """
    Parenthesised comma list: ``(a, b, *rest)``.
    Used both as a value (tuple literal) and as a destructure target.
    """
    elements: list[Expression] = field(default_factory=list)


@dataclass(slots=True)
class StarExpression(Expression):
    """
    ``*name`` inside a tuple / array literal or destructuring target.
    Not valid as a standalone expression.
    """
    name: str


@dataclass(slots=True)
class FStringPart:
    """
    One interpolated slot inside an f-string: ``{expr[!conv][:spec]}``.

    conversion:  ``'r'``, ``'s'``, ``'a'``, or ``None``.
    format_spec: the raw spec string (``'.2f'``, ``'>10'``, …), or ``None``.
    """
    expr:        Expression
    conversion:  str | None = None
    format_spec: str | None = None


@dataclass(slots=True)
class FStringExpression(Expression):
    """
    An interpolated string.

    ``parts`` alternates between plain ``str`` segments and
    ``FStringPart`` objects for ``{...}`` placeholders.
    ``prefix`` is the normalised lexer prefix: ``'f'``, ``'rf'``, etc.
    """
    parts: list[Union[str, FStringPart]]
    prefix: str = "f"


@dataclass(slots=True)
class TernaryExpression(Expression):
    """``condition ? consequent : alternate``"""
    condition: Expression
    consequent: Expression
    alternate: Expression


@dataclass(slots=True)
class WalrusExpression(Expression):
    """``(name := expr)``"""
    target: str
    value: Expression



@dataclass(slots=True)
class GroupExpression(Expression):
    """
    An explicitly parenthesised expression, e.g. ``(a + b)``.

    Preserves the programmer's intent in the AST so that code
    generators can re-emit parentheses faithfully.
    """
    expression: Expression


# ---------------------------------------------------------------------------
# Statement / node hierarchy
# ---------------------------------------------------------------------------


class Node(ABC):
    """Marker base for all statement nodes."""


@dataclass(slots=True)
class ExpressionNode(Node):
    """A bare expression used as a statement (e.g. a call for side-effects)."""
    expr: Expression


@dataclass(slots=True)
class AssignmentNode(Node):
    """
    ``target = value``

    ``target`` may be an ``Identifier``, ``MemberAccessExpression``,
    or ``SubscriptExpression`` — anything that is legally assignable.
    """
    target: Expression
    value: Expression


@dataclass(slots=True)
class CompoundAssignmentNode(Node):
    """
    ``target += value``, ``-=``, ``*=``, ``/=``, ``%=``, ``**=``
    """
    target: Expression
    operator: str               # the full operator string, e.g. "+="
    value: Expression


@dataclass(slots=True)
class AnnotatedAssignmentNode(Node):
    """
    ``target: annotation [= value]``

    ``annotation`` is a full expression so that ``list[int]``,
    ``dict[str, int]``, etc. work via ``SubscriptExpression``.
    """
    target: Expression
    annotation: Expression
    value: Expression | None = None


@dataclass(slots=True)
class WithItem:
    """One context-manager entry in a ``with`` statement."""
    context: Expression
    alias: str | None = None


@dataclass(slots=True)
class WithNode(Node):
    """``with ctx [as name], ... { }``"""
    items: list[WithItem]
    body: BlockNode


@dataclass(slots=True)
class AssertNode(Node):
    """``assert condition [, message]``"""
    condition: Expression
    message: Expression | None = None


@dataclass(slots=True)
class BlockNode(Node):
    """A brace-delimited sequence of statements: ``{ ... }``."""
    body: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class FunctionDeclarationNode(Node):
    """
    A named function declaration: ``function name(params) { body }``.

    Attributes
    ----------
    name:
        The function's identifier.
    params:
        Ordered list of parameter names (strings).
    body:
        The function body as a :class:`BlockNode`.
    """
    name: str
    params: list[Parameter]
    body: BlockNode
    decorators: list[Decorator] = field(default_factory=list)
    return_type: Expression | None = None


@dataclass(slots=True)
class ClassDeclarationNode(Node):
    """
    A class declaration: ``class Name [extends Super] { method* }``

    Attributes
    ----------
    name:       The class identifier.
    superclass: The name of the parent class, or ``None``.
    methods:    Ordered list of method declarations.
    """
    name: str
    bases: list[str]
    body: list[Node]                        # ← methods, assignments, annotations
    decorators: list[Decorator] = field(default_factory=list)


@dataclass(slots=True)
class ReturnNode(Node):
    """
    A ``return`` statement.

    Attributes
    ----------
    value:
        The expression to return, or ``None`` for a bare ``return``.
    """
    value: Expression | None = None


@dataclass(slots=True)
class RaiseNode(Node):
    """A simple raise statement: ``raise Error``"""
    error: Expression | None = None


# ---- imports ----------------------------------------------------------------

@dataclass(slots=True)
class ImportNode(Node):
    """``import module [as alias]``"""
    module: str
    alias: str | None = None


@dataclass(slots=True)
class FromImportNode(Node):
    """``from module import name [as alias], ...``"""
    module: str
    names: list[tuple[str, str | None]]     # (name, alias)


# ---- control flow -----------------------------------------------------------

@dataclass(slots=True)
class IfNode(Node):
    """``if cond { } [elif cond { }]* [else { }]``"""
    condition: Expression
    body: BlockNode
    elifs: list[tuple[Expression, BlockNode]]
    else_body: BlockNode | None = None


@dataclass(slots=True)
class ForNode(Node):
    """``for target in iterable { } [else { }]``"""
    target: str | list[str]        # list[str] for tuple unpacking
    iterable: Expression
    body: BlockNode
    else_body: BlockNode | None = None


@dataclass(slots=True)
class WhileNode(Node):
    """``while cond { } [else { }]``"""
    condition: Expression
    body: BlockNode
    else_body: BlockNode | None = None


# ---- exception handling -----------------------------------------------------

@dataclass(slots=True)
class ExceptHandler:
    """A single ``except`` clause (not a Node; always part of TryNode)."""
    exceptions: list[str]           # empty = bare except
    alias: str | None               # as name
    body: BlockNode


@dataclass(slots=True)
class TryNode(Node):
    """``try { } [except T [as e] { }]* [else { }] [finally { }]``"""
    body: BlockNode
    handlers: list[ExceptHandler]
    else_body: BlockNode | None = None
    finally_body: BlockNode | None = None


# ---- loop control -----------------------------------------------------------

@dataclass(slots=True)
class BreakNode(Node):
    """``break``"""


@dataclass(slots=True)
class ContinueNode(Node):
    """``continue``"""


@dataclass(slots=True)
class PassNode(Node):
    """``pass``"""