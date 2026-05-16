"""
parser
~~~~~~
Syntactic and semantic analysis layer.

Quick imports::

    from parser import Parser, ParseError
    from parser.nodes import FunctionDeclarationNode, AssignmentNode, ...
"""

from .core import Parser, KEYWORDS
from .errors import ParseError
from .nodes import (
    Expression,
    Node,
    Literal,
    Identifier,
    UnaryExpression,
    BinaryExpression,
    MemberAccessExpression,
    CallExpression,
    ArrayExpression,
    GroupExpression,
    ExpressionNode,
    AssignmentNode,
    BlockNode,
    FunctionDeclarationNode,
    ClassDeclarationNode,
    ReturnNode,
)

__all__ = [
    "Parser",
    "KEYWORDS",
    "ParseError",
    "Expression",
    "Node",
    "Literal",
    "Identifier",
    "UnaryExpression",
    "BinaryExpression",
    "MemberAccessExpression",
    "CallExpression",
    "ArrayExpression",
    "GroupExpression",
    "ExpressionNode",
    "AssignmentNode",
    "BlockNode",
    "FunctionDeclarationNode",
    "ClassDeclarationNode",
    "ReturnNode",
]