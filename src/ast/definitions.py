"""
Vibe Language AST — Core Definitions

Design: "The first language designed for autonomous software engineering."
Every node carries location, metadata, and semantic information.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from enum import Enum, auto


# ── Node Kind Enum ──────────────────────────────────────────────
class NodeKind(Enum):
    # Literals
    INT_LIT = auto(); FLOAT_LIT = auto(); TEXT_LIT = auto()
    BOOL_LIT = auto(); BYTE_LIT = auto(); NONE_LIT = auto()
    # Identifiers
    IDENT = auto()
    # Expressions
    BINARY = auto(); UNARY = auto(); CALL = auto()
    FIELD_ACCESS = auto(); INDEX = auto()
    # Statements
    ASSIGN = auto(); RETURN = auto(); YIELD = auto()
    # Control
    WHEN = auto(); OTHERWISE = auto(); LOOP = auto()
    MATCH = auto(); MATCH_ARM = auto()
    # Declarations
    MODULE = auto(); IMPORT = auto(); FROM = auto()
    ENTITY = auto(); ENTITY_PROP = auto()
    ACTION = auto(); ACTION_PARAM = auto()
    FLOW = auto(); FLOW_STEP = auto()
    TRAIT = auto(); TRAIT_METHOD = auto()
    TYPE_ALIAS = auto()
    # Concurrency
    SPAWN = auto(); AWAIT = auto(); CHANNEL = auto()
    # Guarantees / Goals
    GOAL = auto(); CONSTRAINT = auto(); GUARANTEE = auto()
    # Metadata
    METADATA_INTENT = auto(); METADATA_OWNER = auto()
    METADATA_RISK = auto(); METADATA_DEPS = auto()
    METADATA_API = auto(); METADATA_TESTING = auto()
    METADATA_HISTORY = auto(); METADATA_CONTEXT = auto()
    # Memory
    UNSAFE = auto(); OWNED = auto(); BORROWED = auto()
    # Types
    TYPE_PRIM = auto(); TYPE_ARRAY = auto(); TYPE_MAP = auto()
    TYPE_OPTION = auto(); TYPE_RESULT = auto(); TYPE_FUNC = auto()
    TYPE_NAMED = auto(); TYPE_TUPLE = auto()
    TYPE_UNCERTAIN = auto()  # Number<confidence>
    # Top-level
    PROGRAM = auto(); BLOCK = auto()
    # Patterns
    PAT_LITERAL = auto(); PAT_IDENT = auto(); PAT_WILDCARD = auto()
    PAT_ENUM = auto()


# ── Enums ───────────────────────────────────────────────────────
class BinaryOp(Enum):
    ADD = '+'; SUB = '-'; MUL = '*'; DIV = '/'; MOD = '%'; POW = '**'
    EQ = '=='; NEQ = '!='; LT = '<'; LTE = '<='; GT = '>'; GTE = '>='
    AND = 'and'; OR = 'or'
    BIT_AND = '&'; BIT_OR = '|'; BIT_XOR = '^'
    SHL = '<<'; SHR = '>>'
    ASSIGN = '='; ADD_ASSIGN = '+='; SUB_ASSIGN = '-='
    MUL_ASSIGN = '*='; DIV_ASSIGN = '/='; MOD_ASSIGN = '%='

class UnaryOp(Enum):
    NOT = 'not'; NEG = '-'; BIT_NOT = '~'
    REF = '&'; DEREF = '*'
    INC = '++'; DEC = '--'

class PrimitiveType(Enum):
    TEXT = 'Text'; INT = 'Int'; FLOAT = 'Float'
    BOOL = 'Bool'; BYTE = 'Byte'; VOID = 'Void'
    ANY = 'Any'; NEVER = 'Never'

class RiskLevel(Enum):
    LOW = 'low'; MEDIUM = 'medium'; HIGH = 'high'; CRITICAL = 'critical'


# ── Source Location ──────────────────────────────────────────────
@dataclass
class Loc:
    file: str = ''
    line: int = 0; col: int = 0; end_line: int = 0; end_col: int = 0

    def merge(self, other: 'Loc') -> 'Loc':
        return Loc(self.file, self.line, self.col, other.end_line, other.end_col)


# ── Base Node ───────────────────────────────────────────────────
@dataclass
class Node:
    kind: NodeKind = NodeKind.PROGRAM
    loc: Loc = field(default_factory=Loc)


# ── Types ───────────────────────────────────────────────────────
@dataclass
class TypeNode(Node):
    kind: NodeKind = NodeKind.TYPE_PRIM
    name: str = ''

@dataclass
class ArrayType(Node):
    kind: NodeKind = NodeKind.TYPE_ARRAY
    elem: Optional[TypeNode] = None

@dataclass
class MapType(Node):
    kind: NodeKind = NodeKind.TYPE_MAP
    key: Optional[TypeNode] = None
    val: Optional[TypeNode] = None

@dataclass
class OptionType(Node):
    kind: NodeKind = NodeKind.TYPE_OPTION
    inner: Optional[TypeNode] = None

@dataclass
class ResultType(Node):
    kind: NodeKind = NodeKind.TYPE_RESULT
    inner: Optional[TypeNode] = None
    err: Optional[TypeNode] = None

@dataclass
class FuncType(Node):
    kind: NodeKind = NodeKind.TYPE_FUNC
    params: List[TypeNode] = field(default_factory=list)
    ret: Optional[TypeNode] = None

@dataclass
class TupleType(Node):
    kind: NodeKind = NodeKind.TYPE_TUPLE
    elems: List[TypeNode] = field(default_factory=list)

@dataclass
class UncertainType(Node):
    kind: NodeKind = NodeKind.TYPE_UNCERTAIN
    inner: Optional[TypeNode] = None
    confidence: float = 1.0


# ── Expressions ─────────────────────────────────────────────────
@dataclass
class Expr(Node):
    pass

@dataclass
class IntLit(Expr):
    kind: NodeKind = NodeKind.INT_LIT; value: int = 0

@dataclass
class FloatLit(Expr):
    kind: NodeKind = NodeKind.FLOAT_LIT; value: float = 0.0

@dataclass
class TextLit(Expr):
    kind: NodeKind = NodeKind.TEXT_LIT; value: str = ''

@dataclass
class BoolLit(Expr):
    kind: NodeKind = NodeKind.BOOL_LIT; value: bool = False

@dataclass
class ByteLit(Expr):
    kind: NodeKind = NodeKind.BYTE_LIT; value: bytes = b''

@dataclass
class NoneLit(Expr):
    kind: NodeKind = NodeKind.NONE_LIT

@dataclass
class Ident(Expr):
    kind: NodeKind = NodeKind.IDENT; name: str = ''

@dataclass
class BinaryExpr(Expr):
    kind: NodeKind = NodeKind.BINARY
    op: BinaryOp = BinaryOp.ADD
    left: Optional[Expr] = None
    right: Optional[Expr] = None

@dataclass
class UnaryExpr(Expr):
    kind: NodeKind = NodeKind.UNARY
    op: UnaryOp = UnaryOp.NOT
    operand: Optional[Expr] = None

@dataclass
class CallExpr(Expr):
    kind: NodeKind = NodeKind.CALL
    func: Optional[Expr] = None
    args: List[Expr] = field(default_factory=list)

@dataclass
class FieldAccess(Expr):
    kind: NodeKind = NodeKind.FIELD_ACCESS
    obj: Optional[Expr] = None
    field: str = ''

@dataclass
class IndexExpr(Expr):
    kind: NodeKind = NodeKind.INDEX
    obj: Optional[Expr] = None
    idx: Optional[Expr] = None

@dataclass
class SpawnExpr(Expr):
    kind: NodeKind = NodeKind.SPAWN
    call: Optional[CallExpr] = None

@dataclass
class AwaitExpr(Expr):
    kind: NodeKind = NodeKind.AWAIT
    operand: Optional[Expr] = None


# ── Statements ──────────────────────────────────────────────────
@dataclass
class Stmt(Node):
    pass

@dataclass
class Assign(Stmt):
    kind: NodeKind = NodeKind.ASSIGN
    target: Optional[Expr] = None
    value: Optional[Expr] = None
    op: BinaryOp = BinaryOp.ASSIGN

@dataclass
class Return(Stmt):
    kind: NodeKind = NodeKind.RETURN
    value: Optional[Expr] = None

@dataclass
class Yield(Stmt):
    kind: NodeKind = NodeKind.YIELD
    value: Optional[Expr] = None


# ── Control Flow ────────────────────────────────────────────────
@dataclass
class Block(Node):
    kind: NodeKind = NodeKind.BLOCK
    stmts: List[Stmt] = field(default_factory=list)

@dataclass
class WhenBranch(Node):
    kind: NodeKind = NodeKind.WHEN
    cond: Optional[Expr] = None
    body: Optional[Block] = None

@dataclass
class WhenStmt(Stmt):
    kind: NodeKind = NodeKind.WHEN
    branches: List[WhenBranch] = field(default_factory=list)
    otherwise: Optional[Block] = None

@dataclass
class LoopStmt(Stmt):
    kind: NodeKind = NodeKind.LOOP
    var: str = ''
    iterable: Optional[Expr] = None
    body: Optional[Block] = None

@dataclass
class MatchArm(Node):
    kind: NodeKind = NodeKind.MATCH_ARM
    pattern: Optional[Node] = None
    body: Optional[Block] = None

@dataclass
class MatchStmt(Stmt):
    kind: NodeKind = NodeKind.MATCH
    expr: Optional[Expr] = None
    arms: List[MatchArm] = field(default_factory=list)


# ── Declarations ────────────────────────────────────────────────
@dataclass
class Decl(Node):
    pass

@dataclass
class ModuleDecl(Decl):
    kind: NodeKind = NodeKind.MODULE
    name: str = ''
    metadata: 'Metadata' = field(default_factory=lambda: Metadata())

@dataclass
class ImportDecl(Decl):
    kind: NodeKind = NodeKind.IMPORT
    path: str = ''
    alias: str = ''

@dataclass
class FromDecl(Decl):
    kind: NodeKind = NodeKind.FROM
    module: str = ''
    names: List[str] = field(default_factory=list)

@dataclass
class EntityProp(Node):
    kind: NodeKind = NodeKind.ENTITY_PROP
    name: str = ''
    type: Optional[TypeNode] = None
    meta: Dict[str, Any] = field(default_factory=dict)  # e.g. secret, indexed

@dataclass
class EntityDecl(Decl):
    kind: NodeKind = NodeKind.ENTITY
    name: str = ''
    props: List[EntityProp] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)

@dataclass
class ActionParam(Node):
    kind: NodeKind = NodeKind.ACTION_PARAM
    name: str = ''
    type: Optional[TypeNode] = None
    default: Optional[Expr] = None

@dataclass
class ActionDecl(Decl):
    kind: NodeKind = NodeKind.ACTION
    name: str = ''
    params: List[ActionParam] = field(default_factory=list)
    returns: Optional[TypeNode] = None
    body: Optional[Block] = None
    metadata: 'Metadata' = field(default_factory=lambda: Metadata())
    is_pure: bool = False   # proc vs action
    is_async: bool = False

@dataclass
class FlowStep(Node):
    kind: NodeKind = NodeKind.FLOW_STEP
    name: str = ''
    args: List[Expr] = field(default_factory=list)

@dataclass
class FlowDecl(Decl):
    kind: NodeKind = NodeKind.FLOW
    name: str = ''
    input: Optional[TypeNode] = None
    output: Optional[TypeNode] = None
    steps: List[FlowStep] = field(default_factory=list)

@dataclass
class TraitMethod(Node):
    kind: NodeKind = NodeKind.TRAIT_METHOD
    name: str = ''
    params: List[ActionParam] = field(default_factory=list)
    returns: Optional[TypeNode] = None

@dataclass
class TraitDecl(Decl):
    kind: NodeKind = NodeKind.TRAIT
    name: str = ''
    methods: List[TraitMethod] = field(default_factory=list)

@dataclass
class TypeAliasDecl(Decl):
    kind: NodeKind = NodeKind.TYPE_ALIAS
    name: str = ''
    target: Optional[TypeNode] = None


# ── Metadata ────────────────────────────────────────────────────
@dataclass
class MetadataIntent(Node):
    kind: NodeKind = NodeKind.METADATA_INTENT
    lines: List[str] = field(default_factory=list)

@dataclass
class MetadataOwner(Node):
    kind: NodeKind = NodeKind.METADATA_OWNER
    value: str = ''

@dataclass
class MetadataRisk(Node):
    kind: NodeKind = NodeKind.METADATA_RISK
    value: RiskLevel = RiskLevel.LOW

@dataclass
class MetadataDeps(Node):
    kind: NodeKind = NodeKind.METADATA_DEPS
    items: List[str] = field(default_factory=list)

@dataclass
class MetadataAPI(Node):
    kind: NodeKind = NodeKind.METADATA_API
    items: List[str] = field(default_factory=list)

@dataclass
class MetadataTesting(Node):
    kind: NodeKind = NodeKind.METADATA_TESTING
    unit: Optional[float] = None
    integration: Optional[float] = None
    threshold: Optional[float] = None

@dataclass
class MetadataHistory(Node):
    kind: NodeKind = NodeKind.METADATA_HISTORY
    lines: List[str] = field(default_factory=list)

@dataclass
class MetadataContext(Node):
    kind: NodeKind = NodeKind.METADATA_CONTEXT
    lines: List[str] = field(default_factory=list)

@dataclass
class Metadata:
    intent: List[str] = field(default_factory=list)
    owner: str = ''
    risk: RiskLevel = RiskLevel.LOW
    deps: List[str] = field(default_factory=list)
    api: List[str] = field(default_factory=list)
    testing: Optional[MetadataTesting] = None
    history: List[str] = field(default_factory=list)
    context: List[str] = field(default_factory=list)
    raw_nodes: List[Node] = field(default_factory=list)


# ── Guarantees / Goals ─────────────────────────────────────────
@dataclass
class GoalDecl(Decl):
    kind: NodeKind = NodeKind.GOAL
    name: str = ''
    description: List[str] = field(default_factory=list)

@dataclass
class ConstraintDecl(Decl):
    kind: NodeKind = NodeKind.CONSTRAINT
    name: str = ''
    value: str = ''

@dataclass
class GuaranteeDecl(Decl):
    kind: NodeKind = NodeKind.GUARANTEE
    name: str = ''
    description: List[str] = field(default_factory=list)


# ── Unsafe / Ownership ─────────────────────────────────────────
@dataclass
class UnsafeBlock(Stmt):
    kind: NodeKind = NodeKind.UNSAFE
    body: Optional[Block] = None


# ── Patterns ────────────────────────────────────────────────────
@dataclass
class PatLiteral(Node):
    kind: NodeKind = NodeKind.PAT_LITERAL
    value: Optional[Expr] = None

@dataclass
class PatIdent(Node):
    kind: NodeKind = NodeKind.PAT_IDENT
    name: str = ''

@dataclass
class PatWildcard(Node):
    kind: NodeKind = NodeKind.PAT_WILDCARD

@dataclass
class PatEnum(Node):
    kind: NodeKind = NodeKind.PAT_ENUM
    enum: str = ''
    variant: str = ''
    binding: str = ''


# ── Program ─────────────────────────────────────────────────────
@dataclass
class Program(Node):
    kind: NodeKind = NodeKind.PROGRAM
    module: Optional[ModuleDecl] = None
    imports: List[ImportDecl] = field(default_factory=list)
    from_imports: List[FromDecl] = field(default_factory=list)
    decls: List[Decl] = field(default_factory=list)
    metadata: Metadata = field(default_factory=Metadata)
