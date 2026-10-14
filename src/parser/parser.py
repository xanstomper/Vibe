"""
Vibe Language Recursive-Descent Parser

Parses the token stream from src.lexer.lexer into the AST defined by
src.ast.definitions.  Handles the full Vibe surface: module, import,
entity, action, proc, flow, trait, when/otherwise, loop, match,
spawn/await, goal/constraint/guarantee, unsafe blocks, metadata, and
all expression types with correct precedence.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from src.lexer.lexer import Token, TT
from src.ast.definitions import (
    # Source location
    Loc,
    # Node kinds
    NodeKind,
    # Enums
    BinaryOp,
    UnaryOp,
    PrimitiveType,
    RiskLevel,
    # Nodes
    TypeNode,
    ArrayType,
    MapType,
    OptionType,
    ResultType,
    FuncType,
    TupleType,
    UncertainType,
    Expr,
    IntLit,
    FloatLit,
    TextLit,
    BoolLit,
    ByteLit,
    NoneLit,
    Ident,
    BinaryExpr,
    UnaryExpr,
    CallExpr,
    FieldAccess,
    IndexExpr,
    SpawnExpr,
    AwaitExpr,
    Stmt,
    Assign,
    Return,
    Yield,
    Block,
    WhenBranch,
    WhenStmt,
    LoopStmt,
    MatchArm,
    MatchStmt,
    Decl,
    ModuleDecl,
    ImportDecl,
    FromDecl,
    EntityProp,
    EntityDecl,
    ActionParam,
    ActionDecl,
    FlowStep,
    FlowDecl,
    TraitMethod,
    TraitDecl,
    TypeAliasDecl,
    Metadata,
    MetadataIntent,
    MetadataOwner,
    MetadataRisk,
    MetadataDeps,
    MetadataAPI,
    MetadataTesting,
    MetadataHistory,
    MetadataContext,
    GoalDecl,
    ConstraintDecl,
    GuaranteeDecl,
    UnsafeBlock,
    PatLiteral,
    PatIdent,
    PatWildcard,
    PatEnum,
    Program,
)


# ── Errors ──────────────────────────────────────────────────────
class ParseError(Exception):
    """Raised when the parser encounters unexpected input."""

    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Parse error at line {token.line}, col {token.col}: {message}")


# ── Operator-precedence tables ──────────────────────────────────
# Maps TT → BinaryOp for binary operators.
_BINARY_OP_MAP: dict[TT, BinaryOp] = {
    TT.PLUS: BinaryOp.ADD,
    TT.MINUS: BinaryOp.SUB,
    TT.STAR: BinaryOp.MUL,
    TT.SLASH: BinaryOp.DIV,
    TT.PERCENT: BinaryOp.MOD,
    TT.CARET: BinaryOp.POW,
    TT.EQ: BinaryOp.EQ,
    TT.NEQ: BinaryOp.NEQ,
    TT.LT: BinaryOp.LT,
    TT.LTE: BinaryOp.LTE,
    TT.GT: BinaryOp.GT,
    TT.GTE: BinaryOp.GTE,
    TT.AND: BinaryOp.AND,
    TT.OR: BinaryOp.OR,
    TT.AMP: BinaryOp.BIT_AND,
    TT.PIPE: BinaryOp.BIT_OR,
}

# Maps TT → UnaryOp for unary prefix operators.
_UNARY_OP_MAP: dict[TT, UnaryOp] = {
    TT.MINUS: UnaryOp.NEG,
    TT.NOT: UnaryOp.NOT,
    TT.TILDE: UnaryOp.BIT_NOT,
    TT.BANG: UnaryOp.DEREF,   # ! used for deref or result error in some contexts
}

# Maps TT → RiskLevel
_RISK_MAP: dict[str, RiskLevel] = {
    'low': RiskLevel.LOW,
    'medium': RiskLevel.MEDIUM,
    'high': RiskLevel.HIGH,
    'critical': RiskLevel.CRITICAL,
}


# ── Parser ──────────────────────────────────────────────────────
class Parser:
    """Recursive-descent parser for the Vibe language."""

    def __init__(self, tokens: List[Token], filename: str = "<input>"):
        self.tokens = tokens
        self.pos = 0
        self.filename = filename
        self.errors: List[ParseError] = []

    # ── Token navigation ────────────────────────────────────────

    def peek(self) -> Token:
        """Return the current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        # Should always have at least EOF
        return self.tokens[-1]

    def peek_ahead(self, offset: int = 1) -> Token:
        """Peek at token at ``self.pos + offset`` without consuming."""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def advance(self) -> Token:
        """Consume and return the current token."""
        tok = self.peek()
        if tok.type != TT.EOF:
            self.pos += 1
        return tok

    def expect(self, tt: TT) -> Token:
        """Consume the current token if it matches *tt*, else raise."""
        tok = self.peek()
        if tok.type != tt:
            raise ParseError(f"Expected {tt.name}, got {tok.type.name} ({tok.value!r})", tok)
        return self.advance()

    def match(self, *types: TT) -> Optional[Token]:
        """Consume current token if its type is in *types*; else return None."""
        if self.peek().type in types:
            return self.advance()
        return None

    def at(self, *types: TT) -> bool:
        """Check whether the current token's type is in *types*."""
        return self.peek().type in types

    def skip_newlines(self):
        """Consume consecutive NEWLINE / INDENT / DEDENT tokens."""
        while self.peek().type in (TT.NEWLINE, TT.INDENT, TT.DEDENT):
            self.advance()

    def skip_single_newline(self) -> bool:
        """Skip exactly one newline (and any trailing whitespace tokens)."""
        if self.peek().type == TT.NEWLINE:
            self.advance()
            self.skip_newlines()
            return True
        return False

    def loc(self) -> Loc:
        """Build a Loc from the current token."""
        tok = self.peek()
        return Loc(file=self.filename, line=tok.line, col=tok.col,
                   end_line=tok.line, end_col=tok.col)

    def loc_from(self, start: Loc) -> Loc:
        """Merge a start Loc with the current position."""
        tok = self.peek()
        return start.merge(Loc(file=self.filename, line=tok.line, col=tok.col,
                               end_line=tok.line, end_col=tok.col))

    # ── Top-level parse ─────────────────────────────────────────

    def parse(self) -> Program:
        """Parse an entire Vibe program."""
        start = self.loc()
        self.skip_newlines()

        # Module declaration
        module: Optional[ModuleDecl] = None
        if self.peek().type == TT.MODULE:
            module = self.parse_module_decl()
            self.skip_newlines()

        # Metadata (intent / owner / risk / depends / …)
        metadata = Metadata()
        metadata, raw_nodes = self.parse_metadata_block()
        self.skip_newlines()

        # Imports
        imports: List[ImportDecl] = []
        from_imports: List[FromDecl] = []
        while self.at(TT.IMPORT, TT.FROM):
            if self.at(TT.IMPORT):
                imports.append(self.parse_import_decl())
            else:
                from_imports.append(self.parse_from_import_decl())
            self.skip_newlines()

        # Declarations
        decls: List[Decl] = []
        while not self.at(TT.EOF):
            decls.append(self.parse_decl())
            self.skip_newlines()

        loc = self.loc_from(start)
        return Program(
            kind=NodeKind.PROGRAM,
            loc=loc,
            module=module,
            imports=imports,
            from_imports=from_imports,
            decls=decls,
            metadata=metadata,
        )

    # ── Module / Import ─────────────────────────────────────────

    def parse_module_decl(self) -> ModuleDecl:
        start = self.loc()
        self.expect(TT.MODULE)
        name_tok = self.expect(TT.IDENT)
        return ModuleDecl(
            kind=NodeKind.MODULE,
            loc=self.loc_from(start),
            name=name_tok.value,
        )

    def parse_import_decl(self) -> ImportDecl:
        start = self.loc()
        self.expect(TT.IMPORT)
        path_parts = [self.expect(TT.IDENT).value]
        while self.at(TT.DOT):
            self.advance()
            path_parts.append(self.expect(TT.IDENT).value)
        path = ".".join(path_parts)
        alias = ""
        # Optional: import foo as bar
        # The lexer has no 'as' keyword, but we can handle it if there's a
        # future alias token.  For now, just return.
        return ImportDecl(
            kind=NodeKind.IMPORT,
            loc=self.loc_from(start),
            path=path,
            alias=alias,
        )

    def parse_from_import_decl(self) -> FromDecl:
        start = self.loc()
        self.expect(TT.FROM)
        # module name
        mod_parts = [self.expect(TT.IDENT).value]
        while self.at(TT.DOT):
            self.advance()
            mod_parts.append(self.expect(TT.IDENT).value)
        module = ".".join(mod_parts)
        self.expect(TT.IMPORT)
        names = [self.expect(TT.IDENT).value]
        while self.at(TT.COMMA):
            self.advance()
            names.append(self.expect(TT.IDENT).value)
        return FromDecl(
            kind=NodeKind.FROM,
            loc=self.loc_from(start),
            module=module,
            names=names,
        )

    # ── Metadata ────────────────────────────────────────────────

    def parse_metadata_block(self) -> Tuple[Metadata, list]:
        """Parse optional metadata keywords (intent, owner, risk, depends, …).

        Returns a (Metadata, raw_nodes) tuple.  Raw nodes are the
        individual metadata AST nodes (MetadataIntent, …) that may be
        useful for diagnostics.
        """
        metadata = Metadata()
        raw_nodes: list = []

        while self.peek().type == TT.IDENT and self.peek().value in (
            "intent", "owner", "risk", "depends", "api", "testing", "history", "context",
        ):
            key = self.peek().value

            if key == "intent":
                node = self._parse_metadata_intent()
                metadata.intent = node.lines
                raw_nodes.append(node)

            elif key == "owner":
                node = self._parse_metadata_owner()
                metadata.owner = node.value
                raw_nodes.append(node)

            elif key == "risk":
                node = self._parse_metadata_risk()
                metadata.risk = node.value
                raw_nodes.append(node)

            elif key == "depends":
                node = self._parse_metadata_deps()
                metadata.deps = node.items
                raw_nodes.append(node)

            elif key == "api":
                node = self._parse_metadata_api()
                metadata.api = node.items
                raw_nodes.append(node)

            elif key == "testing":
                node = self._parse_metadata_testing()
                metadata.testing = node
                raw_nodes.append(node)

            elif key == "history":
                node = self._parse_metadata_history()
                metadata.history = node.lines
                raw_nodes.append(node)

            elif key == "context":
                node = self._parse_metadata_context()
                metadata.context = node.lines
                raw_nodes.append(node)

            self.skip_newlines()

        return metadata, raw_nodes

    def _parse_metadata_intent(self) -> MetadataIntent:
        start = self.loc()
        self.advance()  # consume 'intent'
        self.expect(TT.COLON)
        self.skip_newlines()
        lines: List[str] = []
        while self.at(TT.TEXT) or self.at(TT.IDENT):
            # Allow string literals or bare identifiers as intent text
            tok = self.advance()
            lines.append(tok.value)
            self.skip_single_newline()
            # If next line is indented or a continuation, keep reading
            if self.at(TT.IDENT) and self.peek().value in (
                "owner", "risk", "depends", "api", "testing", "history", "context",
            ):
                break
        return MetadataIntent(kind=NodeKind.METADATA_INTENT, loc=self.loc_from(start), lines=lines)

    def _parse_metadata_owner(self) -> MetadataOwner:
        start = self.loc()
        self.advance()  # 'owner'
        self.expect(TT.COLON)
        value_tok = self.expect(TT.IDENT)
        return MetadataOwner(kind=NodeKind.METADATA_OWNER, loc=self.loc_from(start),
                             value=value_tok.value)

    def _parse_metadata_risk(self) -> MetadataRisk:
        start = self.loc()
        self.advance()  # 'risk'
        self.expect(TT.COLON)
        value_tok = self.expect(TT.IDENT)
        level = _RISK_MAP.get(value_tok.value.lower(), RiskLevel.LOW)
        return MetadataRisk(kind=NodeKind.METADATA_RISK, loc=self.loc_from(start),
                            value=level)

    def _parse_metadata_deps(self) -> MetadataDeps:
        start = self.loc()
        self.advance()  # 'depends'
        self.expect(TT.COLON)
        self.skip_newlines()
        items: List[str] = []
        # Indented list: each line starts with '-'
        while self.at(TT.MINUS):
            self.advance()  # consume '-'
            name_tok = self.expect(TT.IDENT)
            items.append(name_tok.value)
            self.skip_single_newline()
        return MetadataDeps(kind=NodeKind.METADATA_DEPS, loc=self.loc_from(start),
                            items=items)

    def _parse_metadata_api(self) -> MetadataAPI:
        start = self.loc()
        self.advance()  # 'api'
        self.expect(TT.COLON)
        self.skip_newlines()
        items: List[str] = []
        while self.at(TT.MINUS):
            self.advance()
            name_tok = self.expect(TT.IDENT)
            items.append(name_tok.value)
            self.skip_single_newline()
        return MetadataAPI(kind=NodeKind.METADATA_API, loc=self.loc_from(start),
                           items=items)

    def _parse_metadata_testing(self) -> MetadataTesting:
        start = self.loc()
        self.advance()  # 'testing'
        self.expect(TT.COLON)
        self.skip_newlines()
        node = MetadataTesting(kind=NodeKind.METADATA_TESTING, loc=self.loc_from(start))
        # Parse key: value pairs
        while self.at(TT.IDENT) and self.peek_ahead(1).type == TT.COLON:
            key = self.advance().value
            self.advance()  # ':'
            if key == "unit" and self.at(TT.FLOAT):
                node.unit = float(self.advance().value)
            elif key == "integration" and self.at(TT.FLOAT):
                node.integration = float(self.advance().value)
            elif key == "threshold" and self.at(TT.FLOAT):
                node.threshold = float(self.advance().value)
            elif key == "unit" and self.at(TT.INT):
                node.unit = float(self.advance().value)
            elif key == "integration" and self.at(TT.INT):
                node.integration = float(self.advance().value)
            elif key == "threshold" and self.at(TT.INT):
                node.threshold = float(self.advance().value)
            self.skip_single_newline()
        return node

    def _parse_metadata_history(self) -> MetadataHistory:
        start = self.loc()
        self.advance()  # 'history'
        self.expect(TT.COLON)
        self.skip_newlines()
        lines: List[str] = []
        while self.at(TT.TEXT) or self.at(TT.IDENT):
            tok = self.advance()
            lines.append(tok.value)
            self.skip_single_newline()
        return MetadataHistory(kind=NodeKind.METADATA_HISTORY, loc=self.loc_from(start),
                               lines=lines)

    def _parse_metadata_context(self) -> MetadataContext:
        start = self.loc()
        self.advance()  # 'context'
        self.expect(TT.COLON)
        self.skip_newlines()
        lines: List[str] = []
        while self.at(TT.TEXT) or self.at(TT.IDENT):
            tok = self.advance()
            lines.append(tok.value)
            self.skip_single_newline()
        return MetadataContext(kind=NodeKind.METADATA_CONTEXT, loc=self.loc_from(start),
                               lines=lines)

    # ── Declarations ────────────────────────────────────────────

    def parse_decl(self) -> Decl:
        """Dispatch to the correct declaration parser."""
        tok = self.peek()

        if tok.type == TT.ENTITY:
            return self.parse_entity_decl()
        if tok.type == TT.ACTION:
            return self.parse_action_decl()
        if tok.type == TT.PROC:
            return self.parse_proc_decl()
        if tok.type == TT.FLOW:
            return self.parse_flow_decl()
        if tok.type == TT.TRAIT:
            return self.parse_trait_decl()
        if tok.type == TT.GOAL:
            return self.parse_goal_decl()
        if tok.type == TT.CONSTRAINT:
            return self.parse_constraint_decl()
        if tok.type == TT.GUARANTEE:
            return self.parse_guarantee_decl()

        raise ParseError(
            f"Unexpected token at top level: {tok.type.name} ({tok.value!r})", tok
        )

    # ── Entity ──────────────────────────────────────────────────

    def parse_entity_decl(self) -> EntityDecl:
        start = self.loc()
        self.expect(TT.ENTITY)
        name_tok = self.expect(TT.IDENT)

        # Optional: entity User extends Foo, Bar
        traits: List[str] = []
        # Entity body: indented block of "Name: Type" lines
        self.skip_newlines()
        props: List[EntityProp] = []

        # The body may be on the same line with ':' or on the next (indented)
        if self.at(TT.COLON):
            self.advance()
            self.skip_newlines()

        # Parse indented property lines
        while self.at(TT.IDENT) and not self.peek().value in (
            "entity", "action", "proc", "flow", "trait", "goal", "constraint",
            "guarantee", "unsafe", "module", "import", "from",
        ):
            prop = self.parse_entity_prop()
            props.append(prop)
            self.skip_newlines()

        return EntityDecl(
            kind=NodeKind.ENTITY,
            loc=self.loc_from(start),
            name=name_tok.value,
            props=props,
            traits=traits,
        )

    def parse_entity_prop(self) -> EntityProp:
        """Parse ``Name: Type`` inside an entity block."""
        start = self.loc()
        name_tok = self.expect(TT.IDENT)
        self.expect(TT.COLON)
        type_node = self.parse_type()
        return EntityProp(
            kind=NodeKind.ENTITY_PROP,
            loc=self.loc_from(start),
            name=name_tok.value,
            type=type_node,
        )

    # ── Action ──────────────────────────────────────────────────

    def parse_action_decl(self) -> ActionDecl:
        start = self.loc()
        self.expect(TT.ACTION)
        name_tok = self.expect(TT.IDENT)

        # Parameters
        params: List[ActionParam] = []
        if self.at(TT.LPAREN):
            self.advance()
            params = self.parse_param_list()
            self.expect(TT.RPAREN)

        # Return type
        returns: Optional[TypeNode] = None
        if self.at(TT.ARROW):
            self.advance()
            returns = self.parse_type()

        # Body (indented block)
        body = self.parse_indented_block()

        return ActionDecl(
            kind=NodeKind.ACTION,
            loc=self.loc_from(start),
            name=name_tok.value,
            params=params,
            returns=returns,
            body=body,
            metadata=Metadata(),
            is_pure=False,
            is_async=False,
        )

    # ── Proc (pure function) ────────────────────────────────────

    def parse_proc_decl(self) -> ActionDecl:
        start = self.loc()
        self.expect(TT.PROC)
        name_tok = self.expect(TT.IDENT)

        params: List[ActionParam] = []
        if self.at(TT.LPAREN):
            self.advance()
            params = self.parse_param_list()
            self.expect(TT.RPAREN)

        returns: Optional[TypeNode] = None
        if self.at(TT.ARROW):
            self.advance()
            returns = self.parse_type()

        body = self.parse_indented_block()

        return ActionDecl(
            kind=NodeKind.ACTION,
            loc=self.loc_from(start),
            name=name_tok.value,
            params=params,
            returns=returns,
            body=body,
            metadata=Metadata(),
            is_pure=True,
            is_async=False,
        )

    def parse_param_list(self) -> List[ActionParam]:
        params: List[ActionParam] = []
        if self.at(TT.RPAREN):
            return params
        while True:
            start = self.loc()
            name_tok = self.expect(TT.IDENT)
            self.expect(TT.COLON)
            type_node = self.parse_type()
            default = None
            if self.at(TT.EQ):
                self.advance()
                default = self.parse_expression()
            params.append(ActionParam(
                kind=NodeKind.ACTION_PARAM,
                loc=self.loc_from(start),
                name=name_tok.value,
                type=type_node,
                default=default,
            ))
            if not self.at(TT.COMMA):
                break
            self.advance()
        return params

    # ── Flow ────────────────────────────────────────────────────

    def parse_flow_decl(self) -> FlowDecl:
        start = self.loc()
        self.expect(TT.FLOW)
        name_tok = self.expect(TT.IDENT)
        self.expect(TT.COLON)
        self.skip_newlines()

        input_type: Optional[TypeNode] = None
        output_type: Optional[TypeNode] = None
        steps: List[FlowStep] = []

        while self.at(TT.IDENT):
            key = self.peek().value
            if key == "input":
                self.advance()
                self.expect(TT.COLON)
                input_type = self.parse_type()
                self.skip_newlines()
            elif key == "output":
                self.advance()
                self.expect(TT.COLON)
                output_type = self.parse_type()
                self.skip_newlines()
            elif key == "step":
                self.advance()
                step_name = self.expect(TT.IDENT)
                steps.append(FlowStep(
                    kind=NodeKind.FLOW_STEP,
                    loc=self.loc_from(start),
                    name=step_name.value,
                ))
                self.skip_newlines()
            else:
                break

        return FlowDecl(
            kind=NodeKind.FLOW,
            loc=self.loc_from(start),
            name=name_tok.value,
            input=input_type,
            output=output_type,
            steps=steps,
        )

    # ── Trait ───────────────────────────────────────────────────

    def parse_trait_decl(self) -> TraitDecl:
        start = self.loc()
        self.expect(TT.TRAIT)
        name_tok = self.expect(TT.IDENT)
        self.expect(TT.COLON)
        self.skip_newlines()

        methods: List[TraitMethod] = []
        while self.at(TT.ACTION, TT.PROC):
            method = self.parse_trait_method()
            methods.append(method)
            self.skip_newlines()

        return TraitDecl(
            kind=NodeKind.TRAIT,
            loc=self.loc_from(start),
            name=name_tok.value,
            methods=methods,
        )

    def parse_trait_method(self) -> TraitMethod:
        start = self.loc()
        # Consume action/proc keyword (we don't care which for a trait sig)
        self.advance()
        name_tok = self.expect(TT.IDENT)

        params: List[ActionParam] = []
        if self.at(TT.LPAREN):
            self.advance()
            params = self.parse_param_list()
            self.expect(TT.RPAREN)

        returns: Optional[TypeNode] = None
        if self.at(TT.ARROW):
            self.advance()
            returns = self.parse_type()

        # Trait methods may have no body; skip a colon + block if present
        if self.at(TT.COLON):
            self.advance()
            self.parse_indented_block()

        return TraitMethod(
            kind=NodeKind.TRAIT_METHOD,
            loc=self.loc_from(start),
            name=name_tok.value,
            params=params,
            returns=returns,
        )

    # ── Goal / Constraint / Guarantee ───────────────────────────

    def parse_goal_decl(self) -> GoalDecl:
        start = self.loc()
        self.expect(TT.GOAL)
        self.expect(TT.COLON)
        desc = self._collect_description()
        return GoalDecl(
            kind=NodeKind.GOAL,
            loc=self.loc_from(start),
            name="",
            description=desc,
        )

    def parse_constraint_decl(self) -> ConstraintDecl:
        start = self.loc()
        self.expect(TT.CONSTRAINT)
        self.expect(TT.COLON)
        # The rest of the line is the constraint value
        value = self._collect_inline_text()
        return ConstraintDecl(
            kind=NodeKind.CONSTRAINT,
            loc=self.loc_from(start),
            name="",
            value=value,
        )

    def parse_guarantee_decl(self) -> GuaranteeDecl:
        start = self.loc()
        self.expect(TT.GUARANTEE)
        self.expect(TT.COLON)
        desc = self._collect_description()
        return GuaranteeDecl(
            kind=NodeKind.GUARANTEE,
            loc=self.loc_from(start),
            name="",
            description=desc,
        )

    def _collect_description(self) -> List[str]:
        """Collect indented description lines after a metadata/guarantee colon."""
        self.skip_newlines()
        lines: List[str] = []
        while self.at(TT.TEXT) or self.at(TT.IDENT):
            tok = self.advance()
            # Stop if this is a top-level keyword we should not consume
            if tok.value in (
                "entity", "action", "proc", "flow", "trait", "goal",
                "constraint", "guarantee", "unsafe", "module", "import",
                "from", "intent", "owner", "risk", "depends",
            ):
                break
            lines.append(tok.value)
            self.skip_single_newline()
        return lines

    def _collect_inline_text(self) -> str:
        """Collect the rest of the current line as a single string."""
        parts: List[str] = []
        while not self.at(TT.NEWLINE, TT.EOF, TT.DEDENT, TT.RBRACE):
            tok = self.advance()
            parts.append(tok.value)
        self.skip_single_newline()
        return " ".join(parts)

    # ── Types ───────────────────────────────────────────────────

    def parse_type(self) -> TypeNode:
        """Parse a type annotation.

        Grammar (precedence low → high):
            Type = ArrayType | MapType | OptionType | ResultType
                 | FuncType  | TupleType | PrimType | NamedType
        """
        start = self.loc()

        # ?Type  (Option)
        if self.at(TT.QUESTION):
            self.advance()
            inner = self.parse_type()
            return OptionType(
                kind=NodeKind.TYPE_OPTION,
                loc=self.loc_from(start),
                inner=inner,
            )

        # !Type  (Result)
        if self.at(TT.BANG):
            self.advance()
            inner = self.parse_type()
            return ResultType(
                kind=NodeKind.TYPE_RESULT,
                loc=self.loc_from(start),
                inner=inner,
            )

        # [Type]  (Array)
        if self.at(TT.LBRACKET):
            self.advance()
            elem = self.parse_type()
            self.expect(TT.RBRACKET)
            return ArrayType(
                kind=NodeKind.TYPE_ARRAY,
                loc=self.loc_from(start),
                elem=elem,
            )

        # {K: V}  (Map)
        if self.at(TT.LBRACE):
            self.advance()
            key = self.parse_type()
            self.expect(TT.COLON)
            val = self.parse_type()
            self.expect(TT.RBRACE)
            return MapType(
                kind=NodeKind.TYPE_MAP,
                loc=self.loc_from(start),
                key=key,
                val=val,
            )

        # func(Type, ...) -> Type  (Function type)
        if self.at(TT.IDENT) and self.peek().value == "func":
            self.advance()  # consume 'func'
            self.expect(TT.LPAREN)
            params: List[TypeNode] = []
            if not self.at(TT.RPAREN):
                params.append(self.parse_type())
                while self.at(TT.COMMA):
                    self.advance()
                    params.append(self.parse_type())
            self.expect(TT.RPAREN)
            ret: Optional[TypeNode] = None
            if self.at(TT.ARROW):
                self.advance()
                ret = self.parse_type()
            return FuncType(
                kind=NodeKind.TYPE_FUNC,
                loc=self.loc_from(start),
                params=params,
                ret=ret,
            )

        # Primitive types: Text, Int, Float, Bool, Byte, Void, Any, Never
        if self.at(TT.IDENT) and self.peek().value in (
            "Text", "Int", "Float", "Bool", "Byte", "Void", "Any", "Never",
        ):
            tok = self.advance()
            return TypeNode(
                kind=NodeKind.TYPE_PRIM,
                loc=self.loc_from(start),
                name=tok.value,
            )

        # Named type (user-defined)
        if self.at(TT.IDENT):
            tok = self.advance()

            # Check for generic: TypeName<...>
            if self.at(TT.LT):
                # We treat generic params as part of the name for simplicity
                # e.g. Result<User>
                self.advance()
                args: List[TypeNode] = [self.parse_type()]
                while self.at(TT.COMMA):
                    self.advance()
                    args.append(self.parse_type())
                self.expect(TT.GT)

                # Check for special types: Result<T>, !T etc.
                if tok.value == "Result":
                    inner = args[0] if args else None
                    err = args[1] if len(args) > 1 else None
                    return ResultType(
                        kind=NodeKind.TYPE_RESULT,
                        loc=self.loc_from(start),
                        inner=inner,
                        err=err,
                    )

                # Other generics — store as named with args appended to name
                name_str = tok.value + "<" + ",".join(
                    _type_to_str(a) for a in args
                ) + ">"
                return TypeNode(
                    kind=NodeKind.TYPE_NAMED,
                    loc=self.loc_from(start),
                    name=name_str,
                )

            return TypeNode(
                kind=NodeKind.TYPE_NAMED,
                loc=self.loc_from(start),
                name=tok.value,
            )

        # (Type, ...) — tuple
        if self.at(TT.LPAREN):
            self.advance()
            elems: List[TypeNode] = []
            if not self.at(TT.RPAREN):
                elems.append(self.parse_type())
                while self.at(TT.COMMA):
                    self.advance()
                    elems.append(self.parse_type())
            self.expect(TT.RPAREN)
            return TupleType(
                kind=NodeKind.TYPE_TUPLE,
                loc=self.loc_from(start),
                elems=elems,
            )

        raise ParseError(
            f"Unexpected token in type position: {self.peek().type.name} ({self.peek().value!r})",
            self.peek(),
        )

    # ── Indented blocks ─────────────────────────────────────────

    def parse_indented_block(self) -> Optional[Block]:
        """Parse an indented block of statements (action/proc body).

        The colon may already have been consumed by the caller.
        If the next token is a NEWLINE, the block is indented; otherwise
        the block may be empty or there's an inline body.
        """
        self.skip_newlines()

        # If we're at the start of a new declaration or a dedent, block is empty
        if self.at(TT.DEDENT, TT.EOF) or self.at(
            TT.ENTITY, TT.ACTION, TT.PROC, TT.FLOW, TT.TRAIT,
            TT.GOAL, TT.CONSTRAINT, TT.GUARANTEE, TT.UNSAFE,
            TT.MODULE, TT.IMPORT, TT.FROM,
        ):
            return Block(kind=NodeKind.BLOCK, loc=self.loc())

        stmts: List[Stmt] = []
        while not self.at(TT.DEDENT, TT.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                stmts.append(stmt)
            self.skip_newlines()

        return Block(
            kind=NodeKind.BLOCK,
            loc=self.loc(),
            stmts=stmts,
        )

    # ── Statements ──────────────────────────────────────────────

    def parse_statement(self) -> Optional[Stmt]:
        """Parse a single statement."""
        tok = self.peek()

        # Return
        if tok.type == TT.RETURN:
            return self.parse_return_stmt()

        # Yield
        if tok.type == TT.YIELD:
            return self.parse_yield_stmt()

        # Let / var binding  →  assignment
        if tok.type in (TT.LET, TT.VAR):
            return self.parse_let_stmt()

        # When (if/else)
        if tok.type == TT.WHEN:
            return self.parse_when_stmt()

        # Loop (for-in)
        if tok.type == TT.LOOP:
            return self.parse_loop_stmt()

        # Match
        if tok.type == TT.MATCH:
            return self.parse_match_stmt()

        # Unsafe block
        if tok.type == TT.UNSAFE:
            return self.parse_unsafe_block()

        # Spawn expression statement
        if tok.type == TT.SPAWN:
            expr = self.parse_spawn_expr()
            return Assign(
                kind=NodeKind.ASSIGN,
                loc=expr.loc,
                target=None,
                value=expr,
            )

        # Await expression statement
        if tok.type == TT.AWAIT:
            expr = self.parse_await_expr()
            return Assign(
                kind=NodeKind.ASSIGN,
                loc=expr.loc,
                target=None,
                value=expr,
            )

        # Assignment: ident = expr  (or ident.field = expr, ident[idx] = expr)
        if tok.type == TT.IDENT:
            # Look ahead to see if it's an assignment
            if self._is_assignment():
                return self.parse_assignment()

        # Expression statement (function call, method call, etc.)
        expr = self.parse_expression()
        if expr is not None:
            return Assign(
                kind=NodeKind.ASSIGN,
                loc=expr.loc,
                target=None,
                value=expr,
            )

        return None

    def _is_assignment(self) -> bool:
        """Check if the current line is an assignment (target = expr)."""
        # Save position
        saved = self.pos
        # Skip the identifier
        if self.peek().type == TT.IDENT:
            self.pos += 1
            # Check for assignment operators
            is_assign = self.peek().type in (
                TT.EQ, TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ, TT.SLASH_EQ, TT.PERCENT,
            )
            # Handle field access and indexing in the target
            while self.at(TT.DOT, TT.LBRACKET):
                if self.at(TT.DOT):
                    self.pos += 1
                    if self.peek().type == TT.IDENT:
                        self.pos += 1
                elif self.at(TT.LBRACKET):
                    self.pos += 1
                    # Skip the index expression roughly
                    depth = 1
                    while depth > 0 and self.peek().type != TT.EOF:
                        if self.peek().type == TT.LBRACKET:
                            depth += 1
                        elif self.peek().type == TT.RBRACKET:
                            depth -= 1
                        self.pos += 1
                    is_assign = self.peek().type in (
                        TT.EQ, TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ, TT.SLASH_EQ,
                    )
            self.pos = saved
            return is_assign
        self.pos = saved
        return False

    def parse_return_stmt(self) -> Return:
        start = self.loc()
        self.expect(TT.RETURN)
        value: Optional[Expr] = None
        if not self.at(TT.NEWLINE, TT.EOF, TT.DEDENT, TT.RBRACE):
            value = self.parse_expression()
        return Return(kind=NodeKind.RETURN, loc=self.loc_from(start), value=value)

    def parse_yield_stmt(self) -> Yield:
        start = self.loc()
        self.expect(TT.YIELD)
        value: Optional[Expr] = None
        if not self.at(TT.NEWLINE, TT.EOF, TT.DEDENT, TT.RBRACE):
            value = self.parse_expression()
        return Yield(kind=NodeKind.YIELD, loc=self.loc_from(start), value=value)

    def parse_let_stmt(self) -> Assign:
        """Parse ``let name = expr`` or ``var name = expr`` → Assign."""
        start = self.loc()
        self.advance()  # consume let/var
        name_tok = self.expect(TT.IDENT)
        self.expect(TT.EQ)
        value = self.parse_expression()
        return Assign(
            kind=NodeKind.ASSIGN,
            loc=self.loc_from(start),
            target=Ident(kind=NodeKind.IDENT, loc=start, name=name_tok.value),
            value=value,
            op=BinaryOp.ASSIGN,
        )

    def parse_assignment(self) -> Assign:
        """Parse ``target = expr``."""
        start = self.loc()
        target = self.parse_expression()
        # Determine assignment operator
        op = BinaryOp.ASSIGN
        tok = self.peek()
        if tok.type == TT.PLUS_EQ:
            self.advance()
            op = BinaryOp.ADD_ASSIGN
        elif tok.type == TT.MINUS_EQ:
            self.advance()
            op = BinaryOp.SUB_ASSIGN
        elif tok.type == TT.STAR_EQ:
            self.advance()
            op = BinaryOp.MUL_ASSIGN
        elif tok.type == TT.SLASH_EQ:
            self.advance()
            op = BinaryOp.DIV_ASSIGN
        elif tok.type == TT.EQ:
            self.advance()
            op = BinaryOp.ASSIGN
        else:
            raise ParseError(f"Expected assignment operator, got {tok.type.name}", tok)
        value = self.parse_expression()
        return Assign(
            kind=NodeKind.ASSIGN,
            loc=self.loc_from(start),
            target=target,
            value=value,
            op=op,
        )

    # ── When (if/else) ──────────────────────────────────────────

    def parse_when_stmt(self) -> WhenStmt:
        start = self.loc()
        branches: List[WhenBranch] = []

        # First 'when'
        self.expect(TT.WHEN)
        cond = self.parse_expression()
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        branches.append(WhenBranch(
            kind=NodeKind.WHEN,
            loc=self.loc_from(start),
            cond=cond,
            body=body,
        ))
        self.skip_newlines()

        # Additional 'when' branches (else-if)
        while self.at(TT.WHEN):
            bstart = self.loc()
            self.advance()
            cond2 = self.parse_expression()
            self.expect(TT.COLON)
            body2 = self.parse_indented_block()
            branches.append(WhenBranch(
                kind=NodeKind.WHEN,
                loc=self.loc_from(bstart),
                cond=cond2,
                body=body2,
            ))
            self.skip_newlines()

        # otherwise
        otherwise: Optional[Block] = None
        if self.at(TT.OTHERWISE):
            self.advance()
            self.expect(TT.COLON)
            otherwise = self.parse_indented_block()

        return WhenStmt(
            kind=NodeKind.WHEN,
            loc=self.loc_from(start),
            branches=branches,
            otherwise=otherwise,
        )

    # ── Loop (for-in) ───────────────────────────────────────────

    def parse_loop_stmt(self) -> LoopStmt:
        start = self.loc()
        self.expect(TT.LOOP)
        var_tok = self.expect(TT.IDENT)
        self.expect(TT.IDENT)  # 'in' keyword — lexed as IDENT('in')
        iterable = self.parse_expression()
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        return LoopStmt(
            kind=NodeKind.LOOP,
            loc=self.loc_from(start),
            var=var_tok.value,
            iterable=iterable,
            body=body,
        )

    # ── Match ───────────────────────────────────────────────────

    def parse_match_stmt(self) -> MatchStmt:
        start = self.loc()
        self.expect(TT.MATCH)
        expr = self.parse_expression()
        self.expect(TT.COLON)
        self.skip_newlines()

        arms: List[MatchArm] = []
        while not self.at(TT.DEDENT, TT.EOF):
            arm = self.parse_match_arm()
            arms.append(arm)
            self.skip_newlines()

        return MatchStmt(
            kind=NodeKind.MATCH,
            loc=self.loc_from(start),
            expr=expr,
            arms=arms,
        )

    def parse_match_arm(self) -> MatchArm:
        start = self.loc()
        pattern = self.parse_pattern()
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        return MatchArm(
            kind=NodeKind.MATCH_ARM,
            loc=self.loc_from(start),
            pattern=pattern,
            body=body,
        )

    def parse_pattern(self) -> Node:
        """Parse a match pattern."""
        start = self.loc()
        tok = self.peek()

        # Wildcard: _
        if tok.type == TT.IDENT and tok.value == "_":
            self.advance()
            return PatWildcard(kind=NodeKind.PAT_WILDCARD, loc=self.loc_from(start))

        # Enum pattern: VariantName (binding)
        if tok.type == TT.IDENT:
            name = self.advance().value
            if self.at(TT.LPAREN):
                self.advance()
                binding = ""
                if not self.at(TT.RPAREN):
                    binding = self.expect(TT.IDENT).value
                self.expect(TT.RPAREN)
                return PatEnum(
                    kind=NodeKind.PAT_ENUM,
                    loc=self.loc_from(start),
                    enum="",
                    variant=name,
                    binding=binding,
                )
            # Identifier pattern
            return PatIdent(
                kind=NodeKind.PAT_IDENT,
                loc=self.loc_from(start),
                name=name,
            )

        # Literal pattern
        if tok.type in (TT.INT, TT.FLOAT, TT.TEXT, TT.BOOL, TT.NONE):
            value = self.parse_primary_expr()
            return PatLiteral(
                kind=NodeKind.PAT_LITERAL,
                loc=self.loc_from(start),
                value=value,
            )

        raise ParseError(f"Unexpected token in pattern: {tok.type.name}", tok)

    # ── Unsafe block ────────────────────────────────────────────

    def parse_unsafe_block(self) -> UnsafeBlock:
        start = self.loc()
        self.expect(TT.UNSAFE)
        self.expect(TT.COLON)
        body = self.parse_indented_block()
        return UnsafeBlock(
            kind=NodeKind.UNSAFE,
            loc=self.loc_from(start),
            body=body,
        )

    # ── Spawn / Await ───────────────────────────────────────────

    def parse_spawn_expr(self) -> SpawnExpr:
        start = self.loc()
        self.expect(TT.SPAWN)
        call = self.parse_call_expr()
        return SpawnExpr(
            kind=NodeKind.SPAWN,
            loc=self.loc_from(start),
            call=call,
        )

    def parse_await_expr(self) -> AwaitExpr:
        start = self.loc()
        self.expect(TT.AWAIT)
        operand = self.parse_postfix_expr()
        return AwaitExpr(
            kind=NodeKind.AWAIT,
            loc=self.loc_from(start),
            operand=operand,
        )

    # ── Expressions (precedence climbing) ────────────────────────

    def parse_expression(self) -> Expr:
        """Entry point for expression parsing (lowest precedence)."""
        return self.parse_or_expr()

    def parse_or_expr(self) -> Expr:
        left = self.parse_and_expr()
        while self.at(TT.OR):
            start = left.loc
            self.advance()
            right = self.parse_and_expr()
            left = BinaryExpr(
                kind=NodeKind.BINARY,
                loc=left.loc.merge(right.loc),
                op=BinaryOp.OR,
                left=left,
                right=right,
            )
        return left

    def parse_and_expr(self) -> Expr:
        left = self.parse_equality_expr()
        while self.at(TT.AND):
            start = left.loc
            self.advance()
            right = self.parse_equality_expr()
            left = BinaryExpr(
                kind=NodeKind.BINARY,
                loc=left.loc.merge(right.loc),
                op=BinaryOp.AND,
                left=left,
                right=right,
            )
        return left

    def parse_equality_expr(self) -> Expr:
        left = self.parse_comparison_expr()
        while self.at(TT.EQ, TT.NEQ):
            tok = self.advance()
            right = self.parse_comparison_expr()
            op = BinaryOp.EQ if tok.type == TT.EQ else BinaryOp.NEQ
            left = BinaryExpr(
                kind=NodeKind.BINARY,
                loc=left.loc.merge(right.loc),
                op=op,
                left=left,
                right=right,
            )
        return left

    def parse_comparison_expr(self) -> Expr:
        left = self.parse_additive_expr()
        while self.at(TT.LT, TT.LTE, TT.GT, TT.GTE):
            tok = self.advance()
            right = self.parse_additive_expr()
            op_map = {
                TT.LT: BinaryOp.LT, TT.LTE: BinaryOp.LTE,
                TT.GT: BinaryOp.GT, TT.GTE: BinaryOp.GTE,
            }
            left = BinaryExpr(
                kind=NodeKind.BINARY,
                loc=left.loc.merge(right.loc),
                op=op_map[tok.type],
                left=left,
                right=right,
            )
        return left

    def parse_additive_expr(self) -> Expr:
        left = self.parse_multiplicative_expr()
        while self.at(TT.PLUS, TT.MINUS):
            tok = self.advance()
            right = self.parse_multiplicative_expr()
            op = BinaryOp.ADD if tok.type == TT.PLUS else BinaryOp.SUB
            left = BinaryExpr(
                kind=NodeKind.BINARY,
                loc=left.loc.merge(right.loc),
                op=op,
                left=left,
                right=right,
            )
        return left

    def parse_multiplicative_expr(self) -> Expr:
        left = self.parse_power_expr()
        while self.at(TT.STAR, TT.SLASH, TT.PERCENT):
            tok = self.advance()
            right = self.parse_power_expr()
            op_map = {
                TT.STAR: BinaryOp.MUL,
                TT.SLASH: BinaryOp.DIV,
                TT.PERCENT: BinaryOp.MOD,
            }
            left = BinaryExpr(
                kind=NodeKind.BINARY,
                loc=left.loc.merge(right.loc),
                op=op_map[tok.type],
                left=left,
                right=right,
            )
        return left

    def parse_power_expr(self) -> Expr:
        """Power is right-associative."""
        left = self.parse_unary_expr()
        if self.at(TT.CARET):
            self.advance()
            right = self.parse_power_expr()
            return BinaryExpr(
                kind=NodeKind.BINARY,
                loc=left.loc.merge(right.loc),
                op=BinaryOp.POW,
                left=left,
                right=right,
            )
        return left

    def parse_unary_expr(self) -> Expr:
        start = self.loc()
        tok = self.peek()

        if tok.type == TT.MINUS:
            self.advance()
            operand = self.parse_unary_expr()
            return UnaryExpr(
                kind=NodeKind.UNARY,
                loc=self.loc_from(start),
                op=UnaryOp.NEG,
                operand=operand,
            )

        if tok.type == TT.NOT:
            self.advance()
            operand = self.parse_unary_expr()
            return UnaryExpr(
                kind=NodeKind.UNARY,
                loc=self.loc_from(start),
                op=UnaryOp.NOT,
                operand=operand,
            )

        if tok.type == TT.TILDE:
            self.advance()
            operand = self.parse_unary_expr()
            return UnaryExpr(
                kind=NodeKind.UNARY,
                loc=self.loc_from(start),
                op=UnaryOp.BIT_NOT,
                operand=operand,
            )

        if tok.type == TT.SPAWN:
            return self.parse_spawn_expr()

        if tok.type == TT.AWAIT:
            return self.parse_await_expr()

        return self.parse_postfix_expr()

    def parse_postfix_expr(self) -> Expr:
        """Parse postfix operators: call(), .field, [index]."""
        expr = self.parse_primary_expr()

        while True:
            # Function call: expr(args)
            if self.at(TT.LPAREN):
                self.advance()
                args: List[Expr] = []
                if not self.at(TT.RPAREN):
                    args.append(self.parse_expression())
                    while self.at(TT.COMMA):
                        self.advance()
                        args.append(self.parse_expression())
                self.expect(TT.RPAREN)
                expr = CallExpr(
                    kind=NodeKind.CALL,
                    loc=expr.loc.merge(self.loc()),
                    func=expr,
                    args=args,
                )
                continue

            # Field access: expr.field
            if self.at(TT.DOT):
                self.advance()
                field_tok = self.expect(TT.IDENT)
                expr = FieldAccess(
                    kind=NodeKind.FIELD_ACCESS,
                    loc=expr.loc.merge(self.loc()),
                    obj=expr,
                    field=field_tok.value,
                )
                continue

            # Index: expr[index]
            if self.at(TT.LBRACKET):
                self.advance()
                idx = self.parse_expression()
                self.expect(TT.RBRACKET)
                expr = IndexExpr(
                    kind=NodeKind.INDEX,
                    loc=expr.loc.merge(self.loc()),
                    obj=expr,
                    idx=idx,
                )
                continue

            break

        return expr

    def parse_call_expr(self) -> CallExpr:
        """Parse a function call expression (used by spawn)."""
        start = self.loc()
        func = self.parse_postfix_expr()
        # The postfix already handles call(), so if it's not a call, wrap it
        if isinstance(func, CallExpr):
            return func
        return CallExpr(
            kind=NodeKind.CALL,
            loc=self.loc_from(start),
            func=func,
            args=[],
        )

    def parse_primary_expr(self) -> Expr:
        """Parse the highest-precedence primary expressions."""
        start = self.loc()
        tok = self.peek()

        # Integer literal
        if tok.type == TT.INT:
            self.advance()
            return IntLit(
                kind=NodeKind.INT_LIT,
                loc=self.loc_from(start),
                value=int(tok.value),
            )

        # Float literal
        if tok.type == TT.FLOAT:
            self.advance()
            return FloatLit(
                kind=NodeKind.FLOAT_LIT,
                loc=self.loc_from(start),
                value=float(tok.value),
            )

        # String literal
        if tok.type == TT.TEXT:
            self.advance()
            return TextLit(
                kind=NodeKind.TEXT_LIT,
                loc=self.loc_from(start),
                value=tok.value,
            )

        # Byte literal
        if tok.type == TT.BYTE:
            self.advance()
            return ByteLit(
                kind=NodeKind.BYTE_LIT,
                loc=self.loc_from(start),
                value=bytes.fromhex(tok.value),
            )

        # Bool literal
        if tok.type == TT.BOOL:
            self.advance()
            return BoolLit(
                kind=NodeKind.BOOL_LIT,
                loc=self.loc_from(start),
                value=(tok.value == "true"),
            )

        # None literal
        if tok.type == TT.NONE:
            self.advance()
            return NoneLit(
                kind=NodeKind.NONE_LIT,
                loc=self.loc_from(start),
            )

        # Identifier
        if tok.type == TT.IDENT:
            self.advance()
            return Ident(
                kind=NodeKind.IDENT,
                loc=self.loc_from(start),
                name=tok.value,
            )

        # Parenthesized expression
        if tok.type == TT.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TT.RPAREN)
            return expr

        # Array literal: [expr, expr, …]
        if tok.type == TT.LBRACKET:
            self.advance()
            elements: List[Expr] = []
            if not self.at(TT.RBRACKET):
                elements.append(self.parse_expression())
                while self.at(TT.COMMA):
                    self.advance()
                    elements.append(self.parse_expression())
            self.expect(TT.RBRACKET)
            # Represent array literal as a call to a synthetic array constructor
            # For now, return as a tuple-like call
            return CallExpr(
                kind=NodeKind.CALL,
                loc=self.loc_from(start),
                func=Ident(kind=NodeKind.IDENT, loc=start, name="__array__"),
                args=elements,
            )

        raise ParseError(
            f"Unexpected token in expression: {tok.type.name} ({tok.value!r})", tok
        )


# ── Helpers ─────────────────────────────────────────────────────

def _type_to_str(t: TypeNode) -> str:
    """Convert a TypeNode back to a readable string (for generic name)."""
    if isinstance(t, TypeNode) and t.kind == NodeKind.TYPE_PRIM:
        return t.name
    if isinstance(t, TypeNode) and t.kind == NodeKind.TYPE_NAMED:
        return t.name
    if isinstance(t, ResultType):
        inner = _type_to_str(t.inner) if t.inner else "_"
        return f"Result<{inner}>"
    if isinstance(t, OptionType):
        inner = _type_to_str(t.inner) if t.inner else "_"
        return f"?{inner}"
    if isinstance(t, ArrayType):
        return f"[{_type_to_str(t.elem)}]"
    if isinstance(t, MapType):
        return f"{{{_type_to_str(t.key)}: {_type_to_str(t.val)}}}"
    return "?"


# ── Convenience ─────────────────────────────────────────────────

def parse_source(source: str, filename: str = "<input>") -> Program:
    """Tokenize *source* and parse it into a Program AST."""
    from src.lexer.lexer import tokenize
    tokens = tokenize(source, filename)
    parser = Parser(tokens, filename)
    return parser.parse()
