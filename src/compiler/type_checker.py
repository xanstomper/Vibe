"""
Vibe Language Type Checker — Production Implementation

Two-pass type checking:
  Pass 1: Register all declarations (entities, actions, procs, traits, type aliases)
  Pass 2: Check all function/action bodies for type correctness

Handles all Vibe types:
  - Primitives: Text, Int, Float, Bool, Byte, Void, Any, Never
  - Compound: [Type], {K:V}, ?Type, !Type, (T1,T2,...)
  - UncertainType: Number<confidence>
  - Named types: user-defined entities
  - Function types: func(T1, T2) -> T3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Any, Tuple, Union

from src.ast.definitions import (
    # AST nodes
    Program, ModuleDecl, ImportDecl, FromDecl,
    EntityDecl, EntityProp,
    ActionDecl, ActionParam,
    FlowDecl, FlowStep,
    TraitDecl, TraitMethod,
    TypeAliasDecl,
    GoalDecl, ConstraintDecl, GuaranteeDecl,
    # Type nodes
    TypeNode, ArrayType, MapType, OptionType, ResultType,
    FuncType, TupleType, UncertainType,
    # Expressions
    Expr, IntLit, FloatLit, TextLit, BoolLit, ByteLit, NoneLit,
    Ident, BinaryExpr, UnaryExpr, CallExpr, FieldAccess, IndexExpr,
    SpawnExpr, AwaitExpr,
    # Statements
    Stmt, Assign, Return, Yield,
    Block, WhenBranch, WhenStmt, LoopStmt,
    MatchArm, MatchStmt,
    UnsafeBlock,
    # Patterns
    PatLiteral, PatIdent, PatWildcard, PatEnum,
    # Metadata
    Metadata, MetadataRisk,
    # Enums
    NodeKind, BinaryOp, UnaryOp, PrimitiveType, RiskLevel,
    Loc,
)


# ═══════════════════════════════════════════════════════════════════
#  Internal Type Representation
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class VibeType:
    """Internal representation of a Vibe type for type checking."""
    kind: str  # 'primitive', 'array', 'map', 'option', 'result',
               # 'func', 'tuple', 'uncertain', 'named'
    name: str = ''

    # Container inner types
    elem: Optional[VibeType] = None       # array element
    key: Optional[VibeType] = None        # map key
    val: Optional[VibeType] = None        # map value
    inner: Optional[VibeType] = None      # option/result/uncertain inner
    err: Optional[VibeType] = None        # result error type
    confidence: float = 1.0               # uncertain confidence

    # Func types
    params: Tuple[VibeType, ...] = ()
    ret: Optional[VibeType] = None

    # Tuple
    elems: Tuple[VibeType, ...] = ()

    def display(self) -> str:
        """Human-readable type string."""
        if self.kind == 'primitive':
            return self.name
        if self.kind == 'named':
            return self.name
        if self.kind == 'array':
            return f'[{self.elem.display()}]'
        if self.kind == 'map':
            return f'{{{self.key.display()}: {self.val.display()}}}'
        if self.kind == 'option':
            return f'?{self.inner.display()}'
        if self.kind == 'result':
            return f'!{self.inner.display()}'
        if self.kind == 'func':
            param_str = ', '.join(p.display() for p in self.params)
            ret_str = self.ret.display() if self.ret else 'Void'
            return f'func({param_str}) -> {ret_str}'
        if self.kind == 'tuple':
            return f'({", ".join(e.display() for e in self.elems)})'
        if self.kind == 'uncertain':
            return f'Number<{self.confidence}>'
        return self.name or '<unknown>'

    def is_compatible(self, other: VibeType) -> bool:
        """Check if this type is assignable to *other*."""
        # Any accepts everything
        if other.kind == 'primitive' and other.name == 'Any':
            return True
        if self.kind == 'primitive' and self.name == 'Any':
            return True

        # Never is compatible with nothing (bottom type)
        if self.kind == 'primitive' and self.name == 'Never':
            return True

        # Exact kind match
        if self.kind != other.kind:
            # Option/Result unwrapping
            if self.kind == 'option':
                return self.inner.is_compatible(other)
            if other.kind == 'option':
                return self.is_compatible(other.inner)
            if self.kind == 'result':
                return self.inner.is_compatible(other)
            if other.kind == 'result':
                return self.is_compatible(other.inner)
            return False

        # Primitive matching
        if self.kind == 'primitive':
            if self.name == other.name:
                return True
            # Numeric coercion: Int -> Float
            if self.name == 'Int' and other.name == 'Float':
                return True
            return False

        if self.kind == 'named':
            return self.name == other.name

        if self.kind == 'array':
            return self.elem.is_compatible(other.elem) if self.elem and other.elem else False

        if self.kind == 'map':
            return (self.key.is_compatible(other.key) and
                    self.val.is_compatible(other.val))

        if self.kind == 'option':
            return self.inner.is_compatible(other.inner) if self.inner and other.inner else False

        if self.kind == 'result':
            inner_ok = self.inner.is_compatible(other.inner) if self.inner and other.inner else False
            err_ok = self.err.is_compatible(other.err) if self.err and other.err else True
            return inner_ok and err_ok

        if self.kind == 'func':
            if len(self.params) != len(other.params):
                return False
            param_ok = all(p.is_compatible(o) for p, o in zip(self.params, other.params))
            ret_ok = self.ret.is_compatible(other.ret) if self.ret and other.ret else True
            return param_ok and ret_ok

        if self.kind == 'tuple':
            if len(self.elems) != len(other.elems):
                return False
            return all(e.is_compatible(o) for e, o in zip(self.elems, other.elems))

        if self.kind == 'uncertain':
            return self.inner.is_compatible(other.inner) if self.inner and other.inner else False

        return False


# ── Primitive type singletons ────────────────────────────────────
def _prim(name: str) -> VibeType:
    return VibeType(kind='primitive', name=name)

TEXT    = _prim('Text')
INT     = _prim('Int')
FLOAT   = _prim('Float')
BOOL    = _prim('Bool')
BYTE    = _prim('Byte')
VOID    = _prim('Void')
ANY     = _prim('Any')
NEVER   = _prim('Never')

PRIM_MAP: Dict[str, VibeType] = {
    'Text': TEXT, 'Int': INT, 'Float': FLOAT, 'Bool': BOOL,
    'Byte': BYTE, 'Void': VOID, 'Any': ANY, 'Never': NEVER,
}


# ═══════════════════════════════════════════════════════════════════
#  Type-Checking Error
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TypeError_:
    """A single type-checking error with source location."""
    message: str
    line: int = 0
    col: int = 0

    def __str__(self) -> str:
        if self.line:
            return f'line {self.line}:{self.col}: {self.message}'
        return self.message


# ═══════════════════════════════════════════════════════════════════
#  Symbol Table  (scoped)
# ═══════════════════════════════════════════════════════════════════

class SymbolTable:
    """Lexically-scoped symbol table with nested scopes."""

    def __init__(self) -> None:
        self._scopes: List[Dict[str, VibeType]] = [{}]

    def push(self) -> None:
        self._scopes.append({})

    def pop(self) -> None:
        if len(self._scopes) > 1:
            self._scopes.pop()

    def define(self, name: str, typ: VibeType) -> None:
        self._scopes[-1][name] = typ

    def lookup(self, name: str) -> Optional[VibeType]:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def define_in_current(self, name: str, typ: VibeType) -> bool:
        """Return False if already defined in the current scope (re-declaration)."""
        if name in self._scopes[-1]:
            return False
        self._scopes[-1][name] = typ
        return True


# ═══════════════════════════════════════════════════════════════════
#  Declaration Registries  (populated in pass 1)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class EntityInfo:
    name: str
    props: Dict[str, VibeType] = field(default_factory=dict)
    prop_nodes: Dict[str, EntityProp] = field(default_factory=dict)
    traits: List[str] = field(default_factory=list)
    loc: Loc = field(default_factory=Loc)


@dataclass
class ActionInfo:
    name: str
    params: List[Tuple[str, VibeType]] = field(default_factory=list)
    param_nodes: List[ActionParam] = field(default_factory=list)
    return_type: VibeType = field(default_factory=lambda: VOID)
    body_node: Optional[Block] = None
    is_pure: bool = False
    is_async: bool = False
    metadata: Optional[Metadata] = None
    loc: Loc = field(default_factory=Loc)


@dataclass
class TraitInfo:
    name: str
    methods: Dict[str, 'MethodInfo'] = field(default_factory=dict)
    loc: Loc = field(default_factory=Loc)


@dataclass
class MethodInfo:
    name: str
    params: List[Tuple[str, VibeType]] = field(default_factory=list)
    return_type: VibeType = field(default_factory=lambda: VOID)
    loc: Loc = field(default_factory=Loc)


@dataclass
class FlowInfo:
    name: str
    input_type: Optional[VibeType] = None
    output_type: Optional[VibeType] = None
    steps: List[FlowStep] = field(default_factory=list)
    loc: Loc = field(default_factory=Loc)


@dataclass
class TypeAliasInfo:
    name: str
    target: VibeType = field(default_factory=lambda: ANY)
    loc: Loc = field(default_factory=Loc)


# ═══════════════════════════════════════════════════════════════════
#  Type Checker
# ═══════════════════════════════════════════════════════════════════

class TypeChecker:
    """Production-quality two-pass type checker for the Vibe language."""

    def __init__(self) -> None:
        self.symbols = SymbolTable()
        self.errors: List[TypeError_] = []

        # Declaration registries (populated in pass 1)
        self.entities: Dict[str, EntityInfo] = {}
        self.actions: Dict[str, ActionInfo] = {}
        self.traits: Dict[str, TraitInfo] = {}
        self.type_aliases: Dict[str, TypeAliasInfo] = {}
        self.flows: Dict[str, FlowInfo] = {}

        # Current function context
        self._current_action: Optional[ActionInfo] = None

        # Register built-in functions
        self._register_builtins()

    # ── Error helpers ────────────────────────────────────────────

    def _error(self, msg: str, loc: Optional[Loc] = None) -> None:
        line, col = (0, 0)
        if loc:
            line = loc.line
            col = loc.col
        self.errors.append(TypeError_(msg, line, col))

    # ── Type resolution  (AST TypeNode → VibeType) ──────────────

    def resolve_type(self, node: Optional[Union[TypeNode, NodeKind]],
                     loc: Optional[Loc] = None) -> VibeType:
        """Resolve an AST type node to an internal VibeType."""
        if node is None:
            return VOID

        # TypeNode (primitive named type)
        if isinstance(node, TypeNode):
            name = node.name
            if name in PRIM_MAP:
                return PRIM_MAP[name]
            # Check type aliases
            if name in self.type_aliases:
                return self.type_aliases[name].target
            # Named entity
            return VibeType(kind='named', name=name)

        # ArrayType
        if isinstance(node, ArrayType):
            elem = self.resolve_type(node.elem, loc)
            return VibeType(kind='array', elem=elem,
                            name=f'[{elem.display()}]')

        # MapType
        if isinstance(node, MapType):
            k = self.resolve_type(node.key, loc)
            v = self.resolve_type(node.val, loc)
            return VibeType(kind='map', key=k, val=v,
                            name=f'{{{k.display()}: {v.display()}}}')

        # OptionType
        if isinstance(node, OptionType):
            inner = self.resolve_type(node.inner, loc)
            return VibeType(kind='option', inner=inner,
                            name=f'?{inner.display()}')

        # ResultType
        if isinstance(node, ResultType):
            inner = self.resolve_type(node.inner, loc)
            err = self.resolve_type(node.err, loc) if node.err else _prim('Text')
            return VibeType(kind='result', inner=inner, err=err,
                            name=f'!{inner.display()}')

        # FuncType
        if isinstance(node, FuncType):
            params = tuple(self.resolve_type(p, loc) for p in node.params)
            ret = self.resolve_type(node.ret, loc) if node.ret else VOID
            return VibeType(kind='func', params=params, ret=ret)

        # TupleType
        if isinstance(node, TupleType):
            elems = tuple(self.resolve_type(e, loc) for e in node.elems)
            return VibeType(kind='tuple', elems=elems,
                            name=f'({", ".join(e.display() for e in elems)})')

        # UncertainType
        if isinstance(node, UncertainType):
            inner = self.resolve_type(node.inner, loc)
            return VibeType(kind='uncertain', inner=inner,
                            confidence=node.confidence,
                            name=f'Number<{node.confidence}>')

        # Fallback: treat as named type
        return ANY

    # ── Built-in functions ──────────────────────────────────────

    def _register_builtins(self) -> None:
        """Register built-in functions available everywhere."""
        builtins = [
            ActionInfo('print', params=[('_0', TEXT)], return_type=VOID),
            ActionInfo('println', params=[('_0', TEXT)], return_type=VOID),
            ActionInfo('len', params=[('_0', ANY)], return_type=INT),
            ActionInfo('to_string', params=[('_0', ANY)], return_type=TEXT),
            ActionInfo('to_int', params=[('_0', TEXT)], return_type=INT),
            ActionInfo('to_float', params=[('_0', TEXT)], return_type=FLOAT),
            ActionInfo('to_bool', params=[('_0', TEXT)], return_type=BOOL),
            ActionInfo('panic', params=[('_0', TEXT)], return_type=NEVER),
        ]
        for bi in builtins:
            self.actions[bi.name] = bi

    # ═════════════════════════════════════════════════════════════
    #  PASS 1  —  Register Declarations
    # ═════════════════════════════════════════════════════════════

    def pass_one(self, program: Program) -> None:
        """Register all top-level declarations so pass 2 can reference them."""
        for decl in program.decls:
            if isinstance(decl, EntityDecl):
                self._register_entity(decl)
            elif isinstance(decl, ActionDecl):
                self._register_action(decl)
            elif isinstance(decl, FlowDecl):
                self._register_flow(decl)
            elif isinstance(decl, TraitDecl):
                self._register_trait(decl)
            elif isinstance(decl, TypeAliasDecl):
                self._register_type_alias(decl)
            # GoalDecl, ConstraintDecl, GuaranteeDecl are declarative-only
            # (no type-level body to check).

    def _register_entity(self, decl: EntityDecl) -> None:
        props: Dict[str, VibeType] = {}
        prop_nodes: Dict[str, EntityProp] = {}
        for p in decl.props:
            typ = self.resolve_type(p.type, decl.loc)
            if p.name in props:
                self._error(f'Duplicate property "{p.name}" in entity "{decl.name}"',
                            decl.loc)
            props[p.name] = typ
            prop_nodes[p.name] = p
        info = EntityInfo(name=decl.name, props=props, prop_nodes=prop_nodes,
                          traits=list(decl.traits), loc=decl.loc)
        if decl.name in self.entities:
            self._error(f'Duplicate entity definition "{decl.name}"', decl.loc)
        self.entities[decl.name] = info
        # Also register as a named type in the global scope
        self.symbols.define(decl.name,
                            VibeType(kind='named', name=decl.name))

    def _register_action(self, decl: ActionDecl) -> None:
        params: List[Tuple[str, VibeType]] = []
        for p in decl.params:
            typ = self.resolve_type(p.type, decl.loc)
            params.append((p.name, typ))
        ret = self.resolve_type(decl.returns, decl.loc) if decl.returns else VOID
        info = ActionInfo(
            name=decl.name, params=params, param_nodes=list(decl.params),
            return_type=ret, body_node=decl.body,
            is_pure=decl.is_pure, is_async=decl.is_async,
            metadata=decl.metadata, loc=decl.loc,
        )
        if decl.name in self.actions and decl.name not in ('print', 'println', 'len', 'to_string', 'to_int', 'to_float', 'to_bool', 'panic'):
            self._error(f'Duplicate action/proc definition "{decl.name}"', decl.loc)
        self.actions[decl.name] = info
        # Register in symbol table as a callable
        self.symbols.define(decl.name, VibeType(
            kind='func',
            params=tuple(t for _, t in params),
            ret=ret,
        ))

    def _register_flow(self, decl: FlowDecl) -> None:
        inp = self.resolve_type(decl.input, decl.loc) if decl.input else None
        out = self.resolve_type(decl.output, decl.loc) if decl.output else None
        info = FlowInfo(name=decl.name, input_type=inp, output_type=out,
                        steps=list(decl.steps), loc=decl.loc)
        if decl.name in self.flows:
            self._error(f'Duplicate flow definition "{decl.name}"', decl.loc)
        self.flows[decl.name] = info

    def _register_trait(self, decl: TraitDecl) -> None:
        methods: Dict[str, MethodInfo] = {}
        for m in decl.methods:
            params: List[Tuple[str, VibeType]] = []
            for p in m.params:
                typ = self.resolve_type(p.type, decl.loc)
                params.append((p.name, typ))
            ret = self.resolve_type(m.returns, decl.loc) if m.returns else VOID
            methods[m.name] = MethodInfo(name=m.name, params=params,
                                         return_type=ret, loc=decl.loc)
        info = TraitInfo(name=decl.name, methods=methods, loc=decl.loc)
        if decl.name in self.traits:
            self._error(f'Duplicate trait definition "{decl.name}"', decl.loc)
        self.traits[decl.name] = info
        self.symbols.define(decl.name,
                            VibeType(kind='named', name=decl.name))

    def _register_type_alias(self, decl: TypeAliasDecl) -> None:
        target = self.resolve_type(decl.target, decl.loc)
        info = TypeAliasInfo(name=decl.name, target=target, loc=decl.loc)
        if decl.name in self.type_aliases:
            self._error(f'Duplicate type alias "{decl.name}"', decl.loc)
        self.type_aliases[decl.name] = info
        self.symbols.define(decl.name, target)

    # ═════════════════════════════════════════════════════════════
    #  PASS 2  —  Check Bodies
    # ═════════════════════════════════════════════════════════════

    def pass_two(self, program: Program) -> None:
        """Check all action/proc bodies, flow steps, and metadata."""
        for decl in program.decls:
            if isinstance(decl, ActionDecl):
                self._check_action_body(decl)
            elif isinstance(decl, FlowDecl):
                self._check_flow_body(decl)
        # Validate metadata
        self._check_metadata(program.metadata, program.loc)

    # ── Action / Proc body checking ─────────────────────────────

    def _check_action_body(self, decl: ActionDecl) -> None:
        if decl.body is None:
            return
        info = self.actions.get(decl.name)
        if info is None:
            return
        old_action = self._current_action
        self._current_action = info

        self.symbols.push()
        for name, typ in info.params:
            self.symbols.define(name, typ)
        self._check_block(decl.body, expected_return=info.return_type)
        self.symbols.pop()

        self._current_action = old_action

    # ── Block ───────────────────────────────────────────────────

    def _check_block(self, block: Block,
                     expected_return: Optional[VibeType] = None) -> None:
        self.symbols.push()
        for stmt in block.stmts:
            self._check_stmt(stmt, expected_return)
        self.symbols.pop()

    # ── Statement checking ──────────────────────────────────────

    def _check_stmt(self, stmt: Stmt,
                    expected_return: Optional[VibeType] = None) -> None:
        # --- Let / Var assignment via Assign node with special targets ---
        # In the AST, variable declaration is modeled as Assign where target
        # is an Ident and the variable is new.  For now we treat Assign as
        # pure assignment and expect let/var to also go through Assign but
        # with the variable pre-declared.  The parser should create
        # appropriate nodes; here we handle the common cases.

        if isinstance(stmt, Assign):
            self._check_assign(stmt)
            return

        if isinstance(stmt, Return):
            self._check_return(stmt, expected_return)
            return

        if isinstance(stmt, Yield):
            self._check_yield(stmt)
            return

        if isinstance(stmt, WhenStmt):
            self._check_when(stmt, expected_return)
            return

        if isinstance(stmt, LoopStmt):
            self._check_loop(stmt, expected_return)
            return

        if isinstance(stmt, MatchStmt):
            self._check_match(stmt, expected_return)
            return

        if isinstance(stmt, UnsafeBlock):
            if stmt.body:
                self._check_block(stmt.body, expected_return)
            return

        # Expression statement (call, spawn, etc.)
        if isinstance(stmt, Expr):
            self._check_expr(stmt)
            return

        # Fallback for unknown statement kinds
        self._error(f'Unknown statement kind: {type(stmt).__name__}',
                    getattr(stmt, 'loc', None))

    # ── Let / Var (Assign) ──────────────────────────────────────

    def _check_assign(self, stmt: Assign) -> None:
        target = stmt.target
        value = stmt.value
        if target is None or value is None:
            return

        val_type = self._check_expr(value)

        # Compound assignment (+=, -=, etc.)
        if stmt.op != BinaryOp.ASSIGN:
            target_type = self._check_expr(target)
            # Check that op is valid for the types
            if stmt.op in (BinaryOp.ADD_ASSIGN, BinaryOp.SUB_ASSIGN,
                           BinaryOp.MUL_ASSIGN, BinaryOp.DIV_ASSIGN,
                           BinaryOp.MOD_ASSIGN):
                if not self._is_numeric(target_type) and target_type != TEXT:
                    self._error(
                        f'Compound assignment "{stmt.op.value}" not supported for type {target_type.display()}',
                        stmt.loc)
                # Check val_type is compatible
                if not val_type.is_compatible(target_type):
                    self._error(
                        f'Type mismatch in compound assignment: '
                        f'expected {target_type.display()}, got {val_type.display()}',
                        stmt.loc)
                return

        # Simple assignment (=)
        if isinstance(target, Ident):
            existing = self.symbols.lookup(target.name)
            if existing is not None:
                # Variable already declared — check type compatibility
                if not val_type.is_compatible(existing):
                    self._error(
                        f'Type mismatch: variable "{target.name}" has type '
                        f'{existing.display()}, cannot assign {val_type.display()}',
                        stmt.loc)
            else:
                # First assignment — treat as let-binding (declare the var)
                self.symbols.define(target.name, val_type)
        elif isinstance(target, FieldAccess):
            obj_type = self._check_expr(target.obj) if target.obj else ANY
            if not self._check_entity_field(obj_type, target.field, val_type,
                                            stmt.loc, is_write=True):
                pass  # error already reported
        elif isinstance(target, IndexExpr):
            obj_type = self._check_expr(target.obj) if target.obj else ANY
            idx_type = self._check_expr(target.idx) if target.idx else ANY
            if obj_type.kind == 'map':
                if not idx_type.is_compatible(obj_type.key):
                    self._error(
                        f'Map key type mismatch: expected {obj_type.key.display()}, '
                        f'got {idx_type.display()}', stmt.loc)
                if not val_type.is_compatible(obj_type.val):
                    self._error(
                        f'Map value type mismatch: expected {obj_type.val.display()}, '
                        f'got {val_type.display()}', stmt.loc)
            elif obj_type.kind == 'array':
                if not self._is_numeric(idx_type):
                    self._error(f'Array index must be Int, got {idx_type.display()}',
                                stmt.loc)
                if not val_type.is_compatible(obj_type.elem):
                    self._error(
                        f'Array element type mismatch: expected {obj_type.elem.display()}, '
                        f'got {val_type.display()}', stmt.loc)
            else:
                self._error(f'Cannot index-assign on type {obj_type.display()}',
                            stmt.loc)
        else:
            # Let-binding where target is some pattern — check expression
            self._check_expr(target)

    # ── Return ──────────────────────────────────────────────────

    def _check_return(self, stmt: Return,
                      expected_return: Optional[VibeType] = None) -> None:
        if stmt.value is None:
            if expected_return and expected_return != VOID:
                self._error(
                    f'Function must return a value of type {expected_return.display()}',
                    stmt.loc)
            return
        val_type = self._check_expr(stmt.value)
        if expected_return and expected_return != VOID:
            if not val_type.is_compatible(expected_return):
                self._error(
                    f'Return type mismatch: expected {expected_return.display()}, '
                    f'got {val_type.display()}',
                    stmt.loc)

    # ── Yield ───────────────────────────────────────────────────

    def _check_yield(self, stmt: Yield) -> None:
        if stmt.value:
            self._check_expr(stmt.value)

    # ── When (if/else-if/else) ──────────────────────────────────

    def _check_when(self, stmt: WhenStmt,
                    expected_return: Optional[VibeType] = None) -> None:
        for branch in stmt.branches:
            cond_type = self._check_expr(branch.cond) if branch.cond else BOOL
            if cond_type != BOOL and cond_type.kind != 'primitive' or (
                    cond_type.kind == 'primitive' and cond_type.name != 'Bool'):
                self._error(
                    f'When condition must be Bool, got {cond_type.display()}',
                    branch.cond.loc if branch.cond else stmt.loc)
            if branch.body:
                self._check_block(branch.body, expected_return)
        if stmt.otherwise:
            self._check_block(stmt.otherwise, expected_return)

    # ── Loop ────────────────────────────────────────────────────

    def _check_loop(self, stmt: LoopStmt,
                    expected_return: Optional[VibeType] = None) -> None:
        iter_type = self._check_expr(stmt.iterable) if stmt.iterable else ANY
        elem_type = ANY
        if iter_type.kind == 'array':
            elem_type = iter_type.elem
        elif iter_type.kind == 'map':
            # Looping over a map yields keys
            elem_type = iter_type.key
        elif iter_type.kind == 'primitive' and iter_type.name in ('Int', 'Text'):
            elem_type = iter_type
        elif iter_type.kind != 'primitive' or iter_type.name not in ('Any',):
            self._error(
                f'Cannot iterate over type {iter_type.display()}',
                stmt.iterable.loc if stmt.iterable else stmt.loc)

        if stmt.body:
            self.symbols.push()
            if stmt.var:
                self.symbols.define(stmt.var, elem_type)
            self._check_block(stmt.body, expected_return)
            self.symbols.pop()

    # ── Match ───────────────────────────────────────────────────

    def _check_match(self, stmt: MatchStmt,
                     expected_return: Optional[VibeType] = None) -> None:
        expr_type = self._check_expr(stmt.expr) if stmt.expr else ANY

        if not stmt.arms:
            self._error('Match statement must have at least one arm', stmt.loc)
            return

        has_wildcard = False
        for arm in stmt.arms:
            self._check_pattern(arm.pattern, expr_type)
            if isinstance(arm.pattern, PatWildcard):
                has_wildcard = True
            if arm.body:
                self._check_block(arm.body, expected_return)

        # Exhaustiveness check for enum types
        if (expr_type.kind == 'named' and expr_type.name in self.entities):
            pass  # Entity match — no exhaustiveness needed yet
        # For option types, check that Some and None are covered
        if expr_type.kind == 'option':
            covered_some = False
            covered_none = False
            for arm in stmt.arms:
                if isinstance(arm.pattern, PatEnum):
                    if arm.pattern.variant == 'Some':
                        covered_some = True
                    elif arm.pattern.variant == 'None':
                        covered_none = True
                elif isinstance(arm.pattern, PatWildcard):
                    covered_some = True
                    covered_none = True
            if not (covered_some and covered_none):
                missing = []
                if not covered_some:
                    missing.append('Some')
                if not covered_none:
                    missing.append('None')
                self._error(
                    f'Match not exhaustive for ?type: missing {", ".join(missing)}',
                    stmt.loc)

    def _check_pattern(self, pattern, expected_type: VibeType) -> None:
        if pattern is None:
            return
        if isinstance(pattern, PatWildcard):
            return  # Always valid
        if isinstance(pattern, PatIdent):
            self.symbols.define(pattern.name, expected_type)
            return
        if isinstance(pattern, PatLiteral):
            if pattern.value:
                lit_type = self._check_expr(pattern.value)
                if not lit_type.is_compatible(expected_type):
                    self._error(
                        f'Pattern type mismatch: expected {expected_type.display()}, '
                        f'got {lit_type.display()}',
                        pattern.loc)
            return
        if isinstance(pattern, PatEnum):
            # Validate enum variant exists
            if expected_type.kind == 'named':
                entity = self.entities.get(expected_type.name)
                if entity is None:
                    self._error(
                        f'Type {expected_type.name} is not an entity that can be matched',
                        pattern.loc)
                elif pattern.variant not in entity.props:
                    # Variant not found as property — could be a variant name
                    pass  # Entity variants are a future extension
            elif expected_type.kind == 'option':
                if pattern.variant not in ('Some', 'None'):
                    self._error(
                        f'Unknown option variant "{pattern.variant}", expected Some or None',
                        pattern.loc)
            elif expected_type.kind == 'result':
                if pattern.variant not in ('Ok', 'Err'):
                    self._error(
                        f'Unknown result variant "{pattern.variant}", expected Ok or Err',
                        pattern.loc)
            else:
                self._error(
                    f'Cannot match enum pattern on type {expected_type.display()}',
                    pattern.loc)
            # Bind the inner value if present
            if pattern.binding:
                inner_type = expected_type.inner if expected_type.inner else ANY
                self.symbols.define(pattern.binding, inner_type)
            return

    # ── Expression type inference ───────────────────────────────

    def _check_expr(self, expr: Optional[Expr]) -> VibeType:
        if expr is None:
            return VOID

        # Literals
        if isinstance(expr, IntLit):
            return INT
        if isinstance(expr, FloatLit):
            return FLOAT
        if isinstance(expr, TextLit):
            return TEXT
        if isinstance(expr, BoolLit):
            return BOOL
        if isinstance(expr, ByteLit):
            return BYTE
        if isinstance(expr, NoneLit):
            return VibeType(kind='option', inner=ANY, name='?Any')

        # Identifier
        if isinstance(expr, Ident):
            typ = self.symbols.lookup(expr.name)
            if typ is None:
                self._error(f'Undefined variable "{expr.name}"', expr.loc)
                return ANY
            return typ

        # Binary expression
        if isinstance(expr, BinaryExpr):
            return self._check_binary(expr)

        # Unary expression
        if isinstance(expr, UnaryExpr):
            return self._check_unary(expr)

        # Function call
        if isinstance(expr, CallExpr):
            return self._check_call(expr)

        # Field access
        if isinstance(expr, FieldAccess):
            return self._check_field_access(expr)

        # Index expression
        if isinstance(expr, IndexExpr):
            return self._check_index(expr)

        # Spawn
        if isinstance(expr, SpawnExpr):
            if expr.call:
                ret = self._check_call(expr.call)
                return ret
            return VOID

        # Await
        if isinstance(expr, AwaitExpr):
            if expr.operand:
                inner = self._check_expr(expr.operand)
                # If the type is Option or Result, unwrap it
                if inner.kind == 'option':
                    return inner.inner
                if inner.kind == 'result':
                    return inner.inner
                return inner
            return ANY

        # Fallback
        return ANY

    # ── Binary expressions ──────────────────────────────────────

    def _check_binary(self, expr: BinaryExpr) -> VibeType:
        left = self._check_expr(expr.left)
        right = self._check_expr(expr.right)
        op = expr.op

        # ── Arithmetic: +, -, *, /, %, ** ──
        if op in (BinaryOp.ADD, BinaryOp.SUB, BinaryOp.MUL,
                  BinaryOp.DIV, BinaryOp.MOD, BinaryOp.POW):
            # Text concatenation
            if op == BinaryOp.ADD and left == TEXT and right == TEXT:
                return TEXT
            # Int op Int → Int
            if left == INT and right == INT:
                return INT
            # Float op Float → Float
            if left == FLOAT and right == FLOAT:
                return FLOAT
            # Int op Float → Float, Float op Int → Float
            if (left == INT and right == FLOAT) or (left == FLOAT and right == INT):
                return FLOAT
            # Byte op Int → Byte
            if left == BYTE and right == INT:
                return BYTE
            if left == INT and right == BYTE:
                return BYTE
            self._error(
                f'Cannot apply "{op.value}" to {left.display()} and {right.display()}',
                expr.loc)
            return ANY

        # ── Comparison: ==, !=, <, <=, >, >= ──
        if op in (BinaryOp.EQ, BinaryOp.NEQ, BinaryOp.LT, BinaryOp.LTE,
                  BinaryOp.GT, BinaryOp.GTE):
            # Same-type comparison
            if left.is_compatible(right) or right.is_compatible(left):
                return BOOL
            self._error(
                f'Cannot compare {left.display()} and {right.display()}',
                expr.loc)
            return BOOL

        # ── Logical: and, or ──
        if op in (BinaryOp.AND, BinaryOp.OR):
            if left == BOOL and right == BOOL:
                return BOOL
            self._error(
                f'Logical "{op.value}" requires Bool operands, '
                f'got {left.display()} and {right.display()}',
                expr.loc)
            return BOOL

        # ── Bitwise: &, |, ^, <<, >> ──
        if op in (BinaryOp.BIT_AND, BinaryOp.BIT_OR, BinaryOp.BIT_XOR,
                  BinaryOp.SHL, BinaryOp.SHR):
            if left == INT and right == INT:
                return INT
            if left == BYTE and right == BYTE:
                return BYTE
            self._error(
                f'Bitwise "{op.value}" requires Int/Byte operands, '
                f'got {left.display()} and {right.display()}',
                expr.loc)
            return INT

        # Assignment operators inside expressions (rare but possible)
        if op in (BinaryOp.ASSIGN, BinaryOp.ADD_ASSIGN, BinaryOp.SUB_ASSIGN,
                  BinaryOp.MUL_ASSIGN, BinaryOp.DIV_ASSIGN, BinaryOp.MOD_ASSIGN):
            # These should be handled as statements; if they appear as expressions,
            # we just check both sides and return the target type.
            return left

        return ANY

    # ── Unary expressions ───────────────────────────────────────

    def _check_unary(self, expr: UnaryExpr) -> VibeType:
        operand = self._check_expr(expr.operand)
        op = expr.op

        if op == UnaryOp.NEG:
            if operand == INT or operand == FLOAT:
                return operand
            self._error(
                f'Cannot negate {operand.display()}', expr.loc)
            return ANY

        if op == UnaryOp.NOT:
            if operand == BOOL:
                return BOOL
            self._error(
                f'"not" requires Bool operand, got {operand.display()}',
                expr.loc)
            return BOOL

        if op == UnaryOp.BIT_NOT:
            if operand == INT:
                return INT
            self._error(
                f'"~" requires Int operand, got {operand.display()}',
                expr.loc)
            return INT

        if op in (UnaryOp.INC, UnaryOp.DEC):
            if self._is_numeric(operand):
                return operand
            self._error(
                f'Increment/decrement requires numeric type, got {operand.display()}',
                expr.loc)
            return ANY

        if op == UnaryOp.REF:
            # Reference — return the type as-is for now
            return operand
        if op == UnaryOp.DEREF:
            return operand

        return operand

    # ── Function / action call ──────────────────────────────────

    def _check_call(self, expr: CallExpr) -> VibeType:
        # Determine the callee's type
        if isinstance(expr.func, Ident):
            name = expr.func.name
            action = self.actions.get(name)
            if action is None:
                self._error(f'Undefined function/proc "{name}"', expr.loc)
                return ANY
            # Check argument count
            required = len(action.params)
            provided = len(expr.args)
            if provided != required:
                self._error(
                    f'Function "{name}" expects {required} argument(s), '
                    f'got {provided}',
                    expr.loc)
                return action.return_type
            # Check argument types
            for i, ((param_name, param_type), arg) in enumerate(
                    zip(action.params, expr.args)):
                arg_type = self._check_expr(arg)
                if not arg_type.is_compatible(param_type):
                    self._error(
                        f'Argument {i+1} "{param_name}": expected {param_type.display()}, '
                        f'got {arg_type.display()}',
                        arg.loc if hasattr(arg, 'loc') else expr.loc)
            return action.return_type

        # Call on an expression (function-typed value)
        func_type = self._check_expr(expr.func)
        if func_type.kind == 'func':
            # Check argument count
            required = len(func_type.params)
            provided = len(expr.args)
            if provided != required:
                self._error(
                    f'Function expects {required} argument(s), got {provided}',
                    expr.loc)
                return func_type.ret or VOID
            # Check argument types
            for i, (param_type, arg) in enumerate(
                    zip(func_type.params, expr.args)):
                arg_type = self._check_expr(arg)
                if not arg_type.is_compatible(param_type):
                    self._error(
                        f'Argument {i+1}: expected {param_type.display()}, '
                        f'got {arg_type.display()}',
                        arg.loc if hasattr(arg, 'loc') else expr.loc)
            return func_type.ret or VOID

        # If calling on a named type that is an entity, look for constructor
        if func_type.kind == 'named':
            entity = self.entities.get(func_type.name)
            if entity:
                # Entity constructor call
                return func_type
            self._error(f'Cannot call non-function type {func_type.display()}',
                        expr.loc)
            return ANY

        # Method-style call: func.field(args) — treat as field access then call
        if isinstance(expr.func, FieldAccess):
            obj_type = self._check_expr(expr.func.obj)
            field_name = expr.func.field
            if obj_type.kind == 'named':
                entity = self.entities.get(obj_type.name)
                if entity:
                    # Check for method in entity's traits
                    for trait_name in entity.traits:
                        trait_info = self.traits.get(trait_name)
                        if trait_info and field_name in trait_info.methods:
                            method = trait_info.methods[field_name]
                            for i, (param_type, arg) in enumerate(
                                    zip([t for _, t in method.params], expr.args)):
                                arg_type = self._check_expr(arg)
                                if not arg_type.is_compatible(param_type):
                                    self._error(
                                        f'Method argument {i+1}: expected {param_type.display()}, '
                                        f'got {arg_type.display()}',
                                        arg.loc if hasattr(arg, 'loc') else expr.loc)
                            return method.return_type
            self._error(
                f'No method "{field_name}" found on {obj_type.display()}',
                expr.loc)
            return ANY

        self._error(f'Cannot call non-callable type {func_type.display()}',
                    expr.loc)
        return ANY

    # ── Field access ────────────────────────────────────────────

    def _check_field_access(self, expr: FieldAccess) -> VibeType:
        if expr.obj is None:
            return ANY
        obj_type = self._check_expr(expr.obj)
        field_name = expr.field

        if obj_type.kind == 'named':
            entity = self.entities.get(obj_type.name)
            if entity:
                if field_name in entity.props:
                    return entity.props[field_name]
                self._error(
                    f'Entity "{obj_type.name}" has no property "{field_name}"',
                    expr.loc)
                return ANY
            # Check traits
            trait = self.traits.get(obj_type.name)
            if trait:
                if field_name in trait.methods:
                    m = trait.methods[field_name]
                    return VibeType(
                        kind='func',
                        params=tuple(t for _, t in m.params),
                        ret=m.return_type,
                    )
                self._error(
                    f'Trait "{obj_type.name}" has no method "{field_name}"',
                    expr.loc)
                return ANY
            # Type alias
            if obj_type.name in self.type_aliases:
                aliased = self.type_aliases[obj_type.name].target
                return self._check_field_access_inner(aliased, field_name, expr.loc)
            self._error(
                f'Type "{obj_type.name}" does not have field "{field_name}"',
                expr.loc)
            return ANY

        # Array has .length
        if obj_type.kind == 'array':
            if field_name == 'length':
                return INT
            self._error(
                f'Array has no field "{field_name}" (did you mean "length"?)',
                expr.loc)
            return ANY

        # Map has .keys, .values
        if obj_type.kind == 'map':
            if field_name == 'keys':
                return VibeType(kind='array', elem=obj_type.key,
                                name=f'[{obj_type.key.display()}]')
            if field_name == 'values':
                return VibeType(kind='array', elem=obj_type.val,
                                name=f'[{obj_type.val.display()}]')
            self._error(
                f'Map has no field "{field_name}"',
                expr.loc)
            return ANY

        # Option has .is_some, .unwrap
        if obj_type.kind == 'option':
            if field_name == 'is_some':
                return BOOL
            if field_name == 'unwrap':
                return obj_type.inner
            self._error(
                f'Option has no field "{field_name}"',
                expr.loc)
            return ANY

        # Result has .is_ok, .unwrap
        if obj_type.kind == 'result':
            if field_name == 'is_ok':
                return BOOL
            if field_name == 'unwrap':
                return obj_type.inner
            self._error(
                f'Result has no field "{field_name}"',
                expr.loc)
            return ANY

        self._error(
            f'Cannot access field "{field_name}" on type {obj_type.display()}',
            expr.loc)
        return ANY

    def _check_field_access_inner(self, typ: VibeType, field: str,
                                  loc: Loc) -> VibeType:
        """Resolve field access through type aliases."""
        if typ.kind == 'named':
            entity = self.entities.get(typ.name)
            if entity and field in entity.props:
                return entity.props[field]
        if typ.kind == 'array' and field == 'length':
            return INT
        self._error(
            f'Type {typ.display()} has no field "{field}"', loc)
        return ANY

    def _check_entity_field(self, obj_type: VibeType, field: str,
                            assigned_type: VibeType, loc: Loc,
                            is_write: bool = False) -> bool:
        """Check entity field access for assignment. Returns True if valid."""
        if obj_type.kind != 'named':
            self._error(
                f'Cannot access field "{field}" on type {obj_type.display()}',
                loc)
            return False
        entity = self.entities.get(obj_type.name)
        if entity is None:
            self._error(f'Unknown type "{obj_type.name}"', loc)
            return False
        if field not in entity.props:
            self._error(
                f'Entity "{obj_type.name}" has no property "{field}"',
                loc)
            return False
        prop_type = entity.props[field]
        if is_write and not assigned_type.is_compatible(prop_type):
            self._error(
                f'Cannot assign {assigned_type.display()} to property '
                f'"{field}" of type {prop_type.display()}',
                loc)
            return False
        return True

    # ── Index expression ────────────────────────────────────────

    def _check_index(self, expr: IndexExpr) -> VibeType:
        if expr.obj is None:
            return ANY
        obj_type = self._check_expr(expr.obj)
        idx_type = self._check_expr(expr.idx) if expr.idx else ANY

        if obj_type.kind == 'array':
            if not self._is_numeric(idx_type):
                self._error(
                    f'Array index must be Int, got {idx_type.display()}',
                    expr.loc)
            return obj_type.elem

        if obj_type.kind == 'map':
            if not idx_type.is_compatible(obj_type.key):
                self._error(
                    f'Map key type mismatch: expected {obj_type.key.display()}, '
                    f'got {idx_type.display()}',
                    expr.loc)
            return obj_type.val

        # Index on option (unwrap by index is not valid)
        # Index on tuple
        if obj_type.kind == 'tuple':
            if isinstance(expr.idx, IntLit):
                idx_val = expr.idx.value
                if 0 <= idx_val < len(obj_type.elems):
                    return obj_type.elems[idx_val]
                self._error(
                    f'Tuple index {idx_val} out of range '
                    f'(tuple has {len(obj_type.elems)} elements)',
                    expr.loc)
                return ANY
            self._error(
                'Tuple index must be a compile-time integer literal',
                expr.loc)
            return ANY

        self._error(f'Cannot index type {obj_type.display()}', expr.loc)
        return ANY

    # ── Flow step checking ──────────────────────────────────────

    def _check_flow_body(self, decl: FlowDecl) -> None:
        if not decl.steps:
            return
        info = self.flows.get(decl.name)
        if info is None:
            return
        for step in info.steps:
            if step.name not in self.actions:
                self._error(
                    f'Flow step "{step.name}" references undefined action/proc',
                    step.loc)
            else:
                action = self.actions[step.name]
                # Check argument count
                if len(step.args) != len(action.params):
                    self._error(
                        f'Flow step "{step.name}" expects {len(action.params)} '
                        f'argument(s), got {len(step.args)}',
                        step.loc)

    # ── Metadata validation ─────────────────────────────────────

    def _check_metadata(self, meta: Metadata, loc: Loc) -> None:
        # Validate risk level (already an enum, but check raw_nodes for issues)
        for node in meta.raw_nodes:
            if isinstance(node, MetadataRisk):
                if node.value not in RiskLevel:
                    self._error(
                        f'Invalid risk level "{node.value}", '
                        f'expected one of: low, medium, high, critical',
                        node.loc)
            if isinstance(node, MetadataDeps):
                for item in node.items:
                    if not isinstance(item, str):
                        self._error(
                            f'Dependency must be a string, got {type(item).__name__}',
                            node.loc)

        # Validate testing thresholds
        if meta.testing:
            t = meta.testing
            if t.unit is not None and not (0.0 <= t.unit <= 1.0):
                self._error(
                    f'Unit test coverage must be between 0.0 and 1.0, got {t.unit}',
                    loc)
            if t.integration is not None and not (0.0 <= t.integration <= 1.0):
                self._error(
                    f'Integration test coverage must be between 0.0 and 1.0, '
                    f'got {t.integration}',
                    loc)
            if t.threshold is not None and not (0.0 <= t.threshold <= 1.0):
                self._error(
                    f'Testing threshold must be between 0.0 and 1.0, '
                    f'got {t.threshold}',
                    loc)

    # ── Helpers ─────────────────────────────────────────────────

    def _is_numeric(self, typ: VibeType) -> bool:
        return (typ.kind == 'primitive' and
                typ.name in ('Int', 'Float', 'Byte'))


# ═══════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════

def check(program: Program) -> List[TypeError_]:
    """
    Run the full two-pass type checker on a Vibe Program AST.

    Returns a list of type errors (empty list means no errors).
    """
    checker = TypeChecker()
    checker.pass_one(program)
    checker.pass_two(program)
    return checker.errors


# ═══════════════════════════════════════════════════════════════════
#  CLI entry point
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    print('Vibe Type Checker')
    print('Usage: import and call check(program) with a parsed Program AST.')
    sys.exit(0)
