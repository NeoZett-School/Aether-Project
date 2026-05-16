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

from ._internal.nodes import (
    ParameterKind,
    ArgumentKind,
    Parameter,
    Argument,
    Expression,
    Literal,
    Identifier,
    UnaryExpression,
    BinaryExpression,
    MemberAccessExpression,
    CallExpression,
    SubscriptExpression,
    ArrayExpression,
    TupleExpression,
    StarExpression,
    FStringExpression,
    TernaryExpression,
    WalrusExpression,
    GroupExpression,
    Node,
    ExpressionNode,
    AssignmentNode,
    CompoundAssignmentNode,
    AnnotatedAssignmentNode,
    WithItem,
    WithNode,
    AssertNode,
    BlockNode,
    FunctionDeclarationNode,
    ClassDeclarationNode,
    ReturnNode,
    RaiseNode,
    ImportNode,
    FromImportNode,
    IfNode,
    ForNode,
    WhileNode,
    ExceptHandler,
    TryNode,
    BreakNode,
    ContinueNode,
    PassNode
)

__all__ = (
    "ParameterKind",
    "ArgumentKind",
    "Parameter",
    "Argument",
    "Expression",
    "Literal",
    "Identifier",
    "UnaryExpression",
    "BinaryExpression",
    "MemberAccessExpression",
    "CallExpression",
    "SubscriptExpression",
    "ArrayExpression",
    "TupleExpression",
    "StarExpression",
    "FStringExpression",
    "TernaryExpression",
    "WalrusExpression",
    "GroupExpression",
    "Node",
    "ExpressionNode",
    "AssignmentNode",
    "CompoundAssignmentNode",
    "AnnotatedAssignmentNode",
    "WithItem",
    "WithNode",
    "AssertNode",
    "BlockNode",
    "FunctionDeclarationNode",
    "ClassDeclarationNode",
    "ReturnNode",
    "RaiseNode",
    "ImportNode",
    "FromImportNode",
    "IfNode",
    "ForNode",
    "WhileNode",
    "ExceptHandler",
    "TryNode",
    "BreakNode",
    "ContinueNode",
    "PassNode"
)