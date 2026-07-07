"""
Vibe Language AST Definitions

Core data structures representing the abstract syntax tree
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union
from enum import Enum


class NodeType(Enum):
    """AST node types"""
    # Literals
    INT_LIT = "int_literal"
    FLOAT_LIT = "float_literal"
    STRING_LIT = "string_literal"
    BOOL_LIT = "bool_literal"
    CHAR_LIT = "char_literal"
    
    # Identifiers
    IDENTIFIER = "identifier"
    
    # Expressions
    BINARY_OP = "binary_operation"
    UNARY_OP = "unary_operation"
    FUNCTION_CALL = "function_call"
    METHOD_CALL = "method_call"
    INDEX_ACCESS = "index_access"
    FIELD_ACCESS = "field_access"
    TERNARY = "ternary"
    
    # Statements
    LET = "let"
    MUT = "mut"
    ASSIGN = "assignment"
    RETURN = "return"
    IF = "if"
    WHILE = "while"
    FOR = "for"
    SPAWN = "spawn"
    AWAIT = "await"
    MATCH = "match"
    
    # Declarations
    MODULE = "module"
    IMPORT = "import"
    FUNCTION = "function"
    PROC = "procedure"
    STRUCT = "struct"
    ENUM = "enum"
    TRAIT = "trait"
    TYPE_ALIAS = "type_alias"
    
    # Metadata
    INTENT = "intent"
    OWNER = "owner"
    RISK = "risk"
    DEPENDENCIES = "dependencies"
    API_SURFACE = "api_surface"
    TESTING = "testing"
    
    # Types
    PRIMITIVE_TYPE = "primitive_type"
    ARRAY_TYPE = "array_type"
    MAP_TYPE = "map_type"
    OPTIONAL_TYPE = "optional_type"
    RESULT_TYPE = "result_type"
    FUNCTION_TYPE = "function_type"
    NAMED_TYPE = "named_type"
    
    # Other
    BLOCK = "block"
    PROGRAM = "program"
    COMMENT = "comment"


# Operator types
class BinaryOp(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    MOD = "%"
    POW = "**"
    EQ = "=="
    NEQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    AND = "&&"
    OR = "||"
    BIT_AND = "&"
    BIT_OR = "|"
    BIT_XOR = "^"
    SHL = "<<"
    SHR = ">>"
    ASSIGN = "="
    ADD_ASSIGN = "+="
    SUB_ASSIGN = "-="
    MUL_ASSIGN = "*="
    DIV_ASSIGN = "/="
    MOD_ASSIGN = "%="


class UnaryOp(Enum):
    NOT = "!"
    NEG = "-"
    BIT_NOT = "~"
    REF = "&"
    DEREF = "*"
    INCREMENT = "++"
    DECREMENT = "--"


@dataclass
class SourceLocation:
    """Source code location"""
    file: str
    line: int
    column: int
    length: int = 1


# Type nodes
@dataclass
class TypeNode:
    """Base class for type nodes"""
    node_type: NodeType = NodeType.IDENTIFIER
    location: Optional[SourceLocation] = None


@dataclass
class PrimitiveType(TypeNode):
    """Primitive type like int, float, string"""
    name: str = ""
    
    def __post_init__(self):
        self.node_type = NodeType.PRIMITIVE_TYPE


@dataclass
class ArrayType(TypeNode):
    """Array type like [int]"""
    element_type: Optional[TypeNode] = None
    
    def __post_init__(self):
        self.node_type = NodeType.ARRAY_TYPE


@dataclass
class MapType(TypeNode):
    """Map type like {string: int}"""
    key_type: Optional[TypeNode] = None
    value_type: Optional[TypeNode] = None
    
    def __post_init__(self):
        self.node_type = NodeType.MAP_TYPE


@dataclass
class OptionalType(TypeNode):
    """Optional type like ?int"""
    inner_type: Optional[TypeNode] = None
    
    def __post_init__(self):
        self.node_type = NodeType.OPTIONAL_TYPE


@dataclass
class ResultType(TypeNode):
    """Result type like !int"""
    inner_type: Optional[TypeNode] = None
    
    def __post_init__(self):
        self.node_type = NodeType.RESULT_TYPE


@dataclass
class FunctionType(TypeNode):
    """Function type like func(int) -> int"""
    params: List[TypeNode] = field(default_factory=list)
    return_type: Optional[TypeNode] = None
    
    def __post_init__(self):
        self.node_type = NodeType.FUNCTION_TYPE


@dataclass
class NamedType(TypeNode):
    """Named type like User, Color"""
    name: str = ""
    
    def __post_init__(self):
        self.node_type = NodeType.NAMED_TYPE


# Expression nodes
@dataclass
class Expression:
    """Base class for expressions"""
    node_type: NodeType = NodeType.IDENTIFIER
    location: Optional[SourceLocation] = None


@dataclass
class IntLiteral(Expression):
    """Integer literal"""
    value: int = 0
    
    def __post_init__(self):
        self.node_type = NodeType.INT_LIT


@dataclass
class FloatLiteral(Expression):
    """Float literal"""
    value: float = 0.0
    
    def __post_init__(self):
        self.node_type = NodeType.FLOAT_LIT


@dataclass
class StringLiteral(Expression):
    """String literal"""
    value: str = ""
    
    def __post_init__(self):
        self.node_type = NodeType.STRING_LIT


@dataclass
class BoolLiteral(Expression):
    """Boolean literal"""
    value: bool = False
    
    def __post_init__(self):
        self.node_type = NodeType.BOOL_LIT


@dataclass
class CharLiteral(Expression):
    """Character literal"""
    value: str = ""
    
    def __post_init__(self):
        self.node_type = NodeType.CHAR_LIT


@dataclass
class Identifier(Expression):
    """Identifier"""
    name: str = ""
    
    def __post_init__(self):
        self.node_type = NodeType.IDENTIFIER


@dataclass
class BinaryExpression(Expression):
    """Binary operation"""
    op: BinaryOp = BinaryOp.ADD
    left: Optional[Expression] = None
    right: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = NodeType.BINARY_OP


@dataclass
class UnaryExpression(Expression):
    """Unary operation"""
    op: UnaryOp = UnaryOp.NOT
    operand: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = NodeType.UNARY_OP


@dataclass
class FunctionCall(Expression):
    """Function call"""
    function: Optional[Expression] = None
    arguments: List[Expression] = field(default_factory=list)
    
    def __post_init__(self):
        self.node_type = NodeType.FUNCTION_CALL


@dataclass
class MethodCall(Expression):
    """Method call"""
    object: Optional[Expression] = None
    method: str = ""
    arguments: List[Expression] = field(default_factory=list)
    
    def __post_init__(self):
        self.node_type = NodeType.METHOD_CALL


@dataclass
class IndexAccess(Expression):
    """Array/map index access"""
    object: Optional[Expression] = None
    index: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = NodeType.INDEX_ACCESS


@dataclass
class FieldAccess(Expression):
    """Struct field access"""
    object: Optional[Expression] = None
    field: str = ""
    
    def __post_init__(self):
        self.node_type = NodeType.FIELD_ACCESS


@dataclass
class TernaryExpression(Expression):
    """Ternary expression"""
    condition: Optional[Expression] = None
    then_expr: Optional[Expression] = None
    else_expr: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = NodeType.TERNARY


# Statement nodes
@dataclass
class Statement:
    """Base class for statements"""
    node_type: NodeType = NodeType.IDENTIFIER
    location: Optional[SourceLocation] = None


@dataclass
class LetStatement(Statement):
    """Variable declaration"""
    name: str = ""
    type_annotation: Optional[TypeNode] = None
    value: Optional[Expression] = None
    mutable: bool = False
    
    def __post_init__(self):
        self.node_type = NodeType.LET


@dataclass
class AssignmentStatement(Statement):
    """Assignment"""
    target: Optional[Expression] = None
    value: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = NodeType.ASSIGN


@dataclass
class ReturnStatement(Statement):
    """Return statement"""
    value: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = NodeType.RETURN


@dataclass
class Block:
    """Code block"""
    statements: List[Statement] = field(default_factory=list)
    location: Optional[SourceLocation] = None


@dataclass
class IfStatement(Statement):
    """If statement"""
    condition: Optional[Expression] = None
    then_block: Optional[Block] = None
    else_block: Optional[Union[Block, 'IfStatement']] = None
    
    def __post_init__(self):
        self.node_type = NodeType.IF


@dataclass
class WhileStatement(Statement):
    """While loop"""
    condition: Optional[Expression] = None
    body: Optional[Block] = None
    
    def __post_init__(self):
        self.node_type = NodeType.WHILE


@dataclass
class ForStatement(Statement):
    """For loop"""
    variable: str = ""
    iterable: Optional[Expression] = None
    body: Optional[Block] = None
    
    def __post_init__(self):
        self.node_type = NodeType.FOR


@dataclass
class SpawnStatement(Statement):
    """Spawn async task"""
    call: Optional[FunctionCall] = None
    
    def __post_init__(self):
        self.node_type = NodeType.SPAWN


@dataclass
class AwaitExpression(Expression):
    """Await expression"""
    operand: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = NodeType.AWAIT


@dataclass
class MatchArm:
    """Pattern match arm"""
    pattern: Optional['Pattern'] = None
    body: Optional[Union[Block, Expression]] = None


@dataclass
class MatchStatement(Statement):
    """Pattern matching"""
    expression: Optional[Expression] = None
    arms: List[MatchArm] = field(default_factory=list)
    
    def __post_init__(self):
        self.node_type = NodeType.MATCH


# Declaration nodes
@dataclass
class Declaration:
    """Base class for declarations"""
    node_type: NodeType = NodeType.IDENTIFIER
    location: Optional[SourceLocation] = None


@dataclass
class Parameter:
    """Function parameter"""
    name: str = ""
    type_annotation: Optional[TypeNode] = None
    mutable: bool = False


@dataclass
class ModuleMetadata:
    """AI-readable module metadata"""
    intent: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    risk: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    api_surface: List[str] = field(default_factory=list)
    testing: Optional['TestingMetadata'] = None


@dataclass
class TestingMetadata:
    """Testing metadata"""
    unit_coverage: Optional[float] = None
    integration_coverage: Optional[float] = None
    coverage_threshold: Optional[float] = None


@dataclass
class ModuleDeclaration(Declaration):
    """Module declaration"""
    name: str = ""
    metadata: Optional[ModuleMetadata] = None
    
    def __post_init__(self):
        self.node_type = NodeType.MODULE
        if self.metadata is None:
            self.metadata = ModuleMetadata()


@dataclass
class ImportDeclaration(Declaration):
    """Import statement"""
    path: str = ""
    alias: Optional[str] = None
    
    def __post_init__(self):
        self.node_type = NodeType.IMPORT


@dataclass
class FunctionDeclaration(Declaration):
    """Function declaration"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[TypeNode] = None
    body: Optional[Block] = None
    is_async: bool = False
    
    def __post_init__(self):
        self.node_type = NodeType.FUNCTION


@dataclass
class ProcDeclaration(Declaration):
    """Procedure declaration (no side effects)"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[TypeNode] = None
    body: Optional[Block] = None
    
    def __post_init__(self):
        self.node_type = NodeType.PROC


@dataclass
class StructField:
    """Struct field"""
    name: str = ""
    type_annotation: Optional[TypeNode] = None


@dataclass
class StructDeclaration(Declaration):
    """Struct declaration"""
    name: str = ""
    fields: List[StructField] = field(default_factory=list)
    
    def __post_init__(self):
        self.node_type = NodeType.STRUCT


@dataclass
class EnumVariant:
    """Enum variant"""
    name: str = ""
    data: Optional[List[TypeNode]] = None


@dataclass
class EnumDeclaration(Declaration):
    """Enum declaration"""
    name: str = ""
    variants: List[EnumVariant] = field(default_factory=list)
    
    def __post_init__(self):
        self.node_type = NodeType.ENUM


@dataclass
class TraitMethod:
    """Trait method signature"""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[TypeNode] = None


@dataclass
class TraitDeclaration(Declaration):
    """Trait declaration"""
    name: str = ""
    methods: List[TraitMethod] = field(default_factory=list)
    
    def __post_init__(self):
        self.node_type = NodeType.TRAIT


@dataclass
class TypeAliasDeclaration(Declaration):
    """Type alias"""
    name: str = ""
    target: Optional[TypeNode] = None
    
    def __post_init__(self):
        self.node_type = NodeType.TYPE_ALIAS


@dataclass
class Program:
    """Root program node"""
    module: Optional[ModuleDeclaration] = None
    imports: List[ImportDeclaration] = field(default_factory=list)
    declarations: List[Declaration] = field(default_factory=list)
    metadata: Optional[ModuleMetadata] = None
    location: Optional[SourceLocation] = None
    
    def __post_init__(self):
        self.node_type = NodeType.PROGRAM


# Pattern nodes
@dataclass
class Pattern:
    """Base pattern"""
    node_type: str = ""
    location: Optional[SourceLocation] = None


@dataclass
class LiteralPattern(Pattern):
    """Literal pattern"""
    value: Optional[Expression] = None
    
    def __post_init__(self):
        self.node_type = "literal"


@dataclass
class IdentifierPattern(Pattern):
    """Identifier pattern"""
    name: str = ""
    
    def __post_init__(self):
        self.node_type = "identifier"


@dataclass
class WildcardPattern(Pattern):
    """Wildcard pattern"""
    
    def __post_init__(self):
        self.node_type = "wildcard"


@dataclass
class EnumPattern(Pattern):
    """Enum variant pattern"""
    enum_name: str = ""
    variant: str = ""
    binding: Optional[str] = None
    
    def __post_init__(self):
        self.node_type = "enum"
