"""
Vibe Language Parser

Parses token stream into AST
"""

from typing import List, Optional, Union
from dataclasses import dataclass

from src.lexer.lexer import Token, TokenType, LexerError
from src.ast.definitions import (
    SourceLocation, Program, ModuleDeclaration, ImportDeclaration,
    FunctionDeclaration, ProcDeclaration, StructDeclaration, EnumDeclaration,
    TraitDeclaration, TypeAliasDeclaration, Parameter, StructField, EnumVariant,
    TraitMethod, Block, Statement, Expression, TypeNode,
    LetStatement, AssignmentStatement, ReturnStatement, IfStatement,
    WhileStatement, ForStatement, MatchStatement, MatchArm,
    SpawnStatement, AwaitExpression,
    IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, CharLiteral,
    Identifier, BinaryExpression, UnaryExpression, FunctionCall,
    MethodCall, IndexAccess, FieldAccess, TernaryExpression,
    PrimitiveType, ArrayType, MapType, OptionalType, ResultType,
    NamedType, ModuleMetadata, TestingMetadata,
    Pattern, LiteralPattern, IdentifierPattern, WildcardPattern, EnumPattern,
    BinaryOp, UnaryOp
)


class ParseError(Exception):
    """Parse error"""
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Line {token.line}, Column {token.column}: {message}")


class Parser:
    """Vibe language parser"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: List[ParseError] = []
    
    def peek(self) -> Token:
        """Peek at current token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # Return EOF
    
    def peek_next(self) -> Token:
        """Peek at next token"""
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return self.tokens[-1]  # Return EOF
    
    def advance(self) -> Token:
        """Advance to next token"""
        token = self.peek()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token
    
    def expect(self, token_type: TokenType) -> Token:
        """Expect and consume a specific token type"""
        token = self.peek()
        if token.type != token_type:
            raise ParseError(f"Expected {token_type.name}, got {token.type.name}", token)
        return self.advance()
    
    def match(self, *token_types: TokenType) -> Optional[Token]:
        """Match and consume if token type matches"""
        if self.peek().type in token_types:
            return self.advance()
        return None
    
    def skip_newlines(self):
        """Skip newline tokens"""
        while self.peek().type == TokenType.NEWLINE:
            self.advance()
    
    def skip_indentation(self):
        """Skip indentation tokens"""
        while self.peek().type in (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
            self.advance()
    
    def parse(self) -> Program:
        """Parse the entire program"""
        self.skip_newlines()
        
        # Parse module declaration
        module = None
        metadata = ModuleMetadata()
        
        if self.peek().type == TokenType.MODULE:
            module, metadata = self.parse_module_declaration()
        
        # Parse imports
        imports = []
        while self.peek().type == TokenType.IMPORT:
            imports.append(self.parse_import_declaration())
            self.skip_newlines()
        
        # Parse declarations
        declarations = []
        while self.peek().type != TokenType.EOF:
            decl = self.parse_declaration()
            if decl:
                declarations.append(decl)
            self.skip_newlines()
        
        return Program(
            module=module,
            imports=imports,
            declarations=declarations,
            metadata=metadata
        )
    
    def parse_module_declaration(self) -> tuple[ModuleDeclaration, ModuleMetadata]:
        """Parse module declaration and metadata"""
        self.expect(TokenType.MODULE)
        name_token = self.expect(TokenType.IDENTIFIER)
        self.skip_newlines()
        
        metadata = ModuleMetadata()
        
        # Parse metadata blocks
        while self.peek().type in (TokenType.INTENT, TokenType.OWNER, TokenType.RISK,
                                    TokenType.DEPENDENCIES, TokenType.API_SURFACE, TokenType.TESTING):
            meta_type = self.peek().type
            
            if meta_type == TokenType.INTENT:
                self.advance()
                metadata.intent = self.parse_string_list()
            elif meta_type == TokenType.OWNER:
                self.advance()
                self.expect(TokenType.COLON)
                owner_token = self.expect(TokenType.IDENTIFIER)
                metadata.owner = owner_token.value
            elif meta_type == TokenType.RISK:
                self.advance()
                self.expect(TokenType.COLON)
                risk_token = self.expect(TokenType.IDENTIFIER)
                metadata.risk = risk_token.value
            elif meta_type == TokenType.DEPENDENCIES:
                self.advance()
                metadata.dependencies = self.parse_string_list()
            elif meta_type == TokenType.API_SURFACE:
                self.advance()
                metadata.api_surface = self.parse_string_list()
            elif meta_type == TokenType.TESTING:
                self.advance()
                metadata.testing = self.parse_testing_metadata()
            
            self.skip_newlines()
        
        return (
            ModuleDeclaration(name=name_token.value, metadata=metadata),
            metadata
        )
    
    def parse_string_list(self) -> List[str]:
        """Parse a list of strings"""
        items = []
        self.skip_newlines()
        
        if self.peek().type == TokenType.COLON:
            self.advance()
            self.skip_newlines()
        
        while self.peek().type == TokenType.IDENTIFIER or self.peek().type == TokenType.STRING:
            token = self.advance()
            items.append(token.value)
            self.skip_newlines()
        
        return items
    
    def parse_testing_metadata(self) -> TestingMetadata:
        """Parse testing metadata"""
        self.skip_newlines()
        metadata = TestingMetadata()
        
        while self.peek().type in (TokenType.UNIT, TokenType.INTEGRATION, TokenType.COVERAGE, TokenType.THRESHOLD):
            key = self.advance().type
            self.expect(TokenType.COLON)
            
            if key == TokenType.UNIT:
                value_token = self.expect(TokenType.FLOAT)
                metadata.unit_coverage = float(value_token.value)
            elif key == TokenType.INTEGRATION:
                value_token = self.expect(TokenType.FLOAT)
                metadata.integration_coverage = float(value_token.value)
            elif key == TokenType.THRESHOLD:
                value_token = self.expect(TokenType.INT)
                metadata.coverage_threshold = float(value_token.value)
            
            self.skip_newlines()
        
        return metadata
    
    def parse_import_declaration(self) -> ImportDeclaration:
        """Parse import declaration"""
        self.expect(TokenType.IMPORT)
        
        # Parse module path
        path_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.peek().type == TokenType.DOT:
            self.advance()
            path_parts.append(self.expect(TokenType.IDENTIFIER).value)
        
        path = '.'.join(path_parts)
        alias = None
        
        if self.peek().type == TokenType.AS:
            self.advance()
            alias = self.expect(TokenType.IDENTIFIER).value
        
        return ImportDeclaration(path=path, alias=alias)
    
    def parse_declaration(self) -> Optional[Union[FunctionDeclaration, ProcDeclaration, 
                                                   StructDeclaration, EnumDeclaration,
                                                   TraitDeclaration, TypeAliasDeclaration]]:
        """Parse a declaration"""
        token = self.peek()
        
        if token.type == TokenType.FUNC:
            return self.parse_function_declaration()
        elif token.type == TokenType.PROC:
            return self.parse_proc_declaration()
        elif token.type == TokenType.STRUCT:
            return self.parse_struct_declaration()
        elif token.type == TokenType.ENUM:
            return self.parse_enum_declaration()
        elif token.type == TokenType.TRAIT:
            return self.parse_trait_declaration()
        elif token.type == TokenType.TYPE:
            return self.parse_type_alias_declaration()
        else:
            # Skip unknown tokens
            self.advance()
            return None
    
    def parse_function_declaration(self) -> FunctionDeclaration:
        """Parse function declaration"""
        self.expect(TokenType.FUNC)
        name_token = self.expect(TokenType.IDENTIFIER)
        
        # Parse parameters
        self.expect(TokenType.LPAREN)
        parameters = self.parse_parameter_list()
        self.expect(TokenType.RPAREN)
        
        # Parse return type
        return_type = None
        if self.peek().type == TokenType.ARROW:
            self.advance()
            return_type = self.parse_type()
        
        # Parse body
        body = None
        if self.peek().type == TokenType.LBRACE:
            body = self.parse_block()
        
        return FunctionDeclaration(
            name=name_token.value,
            parameters=parameters,
            return_type=return_type,
            body=body
        )
    
    def parse_proc_declaration(self) -> ProcDeclaration:
        """Parse procedure declaration"""
        self.expect(TokenType.PROC)
        name_token = self.expect(TokenType.IDENTIFIER)
        
        # Parse parameters
        self.expect(TokenType.LPAREN)
        parameters = self.parse_parameter_list()
        self.expect(TokenType.RPAREN)
        
        # Parse return type
        return_type = None
        if self.peek().type == TokenType.ARROW:
            self.advance()
            return_type = self.parse_type()
        
        # Parse body
        body = self.parse_block()
        
        return ProcDeclaration(
            name=name_token.value,
            parameters=parameters,
            return_type=return_type,
            body=body
        )
    
    def parse_parameter_list(self) -> List[Parameter]:
        """Parse parameter list"""
        parameters = []
        
        if self.peek().type == TokenType.RPAREN:
            return parameters
        
        while True:
            name_token = self.expect(TokenType.IDENTIFIER)
            self.expect(TokenType.COLON)
            type_node = self.parse_type()
            
            mutable = False
            if self.peek().type == TokenType.MUT:
                self.advance()
                mutable = True
            
            parameters.append(Parameter(
                name=name_token.value,
                type_annotation=type_node,
                mutable=mutable
            ))
            
            if self.peek().type != TokenType.COMMA:
                break
            self.advance()
        
        return parameters
    
    def parse_struct_declaration(self) -> StructDeclaration:
        """Parse struct declaration"""
        self.expect(TokenType.STRUCT)
        name_token = self.expect(TokenType.IDENTIFIER)
        
        self.expect(TokenType.LBRACE)
        fields = []
        
        self.skip_newlines()
        while self.peek().type != TokenType.RBRACE:
            self.skip_newlines()
            field_name = self.expect(TokenType.IDENTIFIER)
            self.expect(TokenType.COLON)
            field_type = self.parse_type()
            
            fields.append(StructField(
                name=field_name.value,
                type_annotation=field_type
            ))
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return StructDeclaration(name=name_token.value, fields=fields)
    
    def parse_enum_declaration(self) -> EnumDeclaration:
        """Parse enum declaration"""
        self.expect(TokenType.ENUM)
        name_token = self.expect(TokenType.IDENTIFIER)
        
        self.expect(TokenType.LBRACE)
        variants = []
        
        self.skip_newlines()
        while self.peek().type != TokenType.RBRACE:
            self.skip_newlines()
            variant_name = self.expect(TokenType.IDENTIFIER).value
            
            data = None
            if self.peek().type == TokenType.LPAREN:
                self.advance()
                data = []
                
                while self.peek().type != TokenType.RPAREN:
                    data.append(self.parse_type())
                    if self.peek().type == TokenType.COMMA:
                        self.advance()
                
                self.expect(TokenType.RPAREN)
            
            variants.append(EnumVariant(name=variant_name, data=data))
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return EnumDeclaration(name=name_token.value, variants=variants)
    
    def parse_trait_declaration(self) -> TraitDeclaration:
        """Parse trait declaration"""
        self.expect(TokenType.TRAIT)
        name_token = self.expect(TokenType.IDENTIFIER)
        
        self.expect(TokenType.LBRACE)
        methods = []
        
        while self.peek().type != TokenType.RBRACE:
            self.expect(TokenType.FUNC)
            method_name = self.expect(TokenType.IDENTIFIER)
            
            self.expect(TokenType.LPAREN)
            parameters = self.parse_parameter_list()
            self.expect(TokenType.RPAREN)
            
            return_type = None
            if self.peek().type == TokenType.ARROW:
                self.advance()
                return_type = self.parse_type()
            
            # Skip body (trait methods are just signatures)
            if self.peek().type == TokenType.LBRACE:
                self.parse_block()
            
            methods.append(TraitMethod(
                name=method_name.value,
                parameters=parameters,
                return_type=return_type
            ))
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return TraitDeclaration(name=name_token.value, methods=methods)
    
    def parse_type_alias_declaration(self) -> TypeAliasDeclaration:
        """Parse type alias declaration"""
        self.expect(TokenType.TYPE)
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ASSIGN)
        target = self.parse_type()
        
        return TypeAliasDeclaration(name=name_token.value, target=target)
    
    def parse_type(self) -> TypeNode:
        """Parse a type"""
        token = self.peek()
        
        # Optional type
        if token.type == TokenType.QUESTION:
            self.advance()
            inner = self.parse_type()
            return OptionalType(inner_type=inner)
        
        # Result type
        if token.type == TokenType.EXCLAMATION:
            self.advance()
            inner = self.parse_type()
            return ResultType(inner_type=inner)
        
        # Array type
        if token.type == TokenType.LBRACKET:
            self.advance()
            element_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            return ArrayType(element_type=element_type)
        
        # Map type
        if token.type == TokenType.LBRACE:
            self.advance()
            key_type = self.parse_type()
            self.expect(TokenType.COLON)
            value_type = self.parse_type()
            self.expect(TokenType.RBRACE)
            return MapType(key_type=key_type, value_type=value_type)
        
        # Function type
        if token.type == TokenType.FUNC:
            self.advance()
            self.expect(TokenType.LPAREN)
            params = []
            while self.peek().type != TokenType.RPAREN:
                params.append(self.parse_type())
                if self.peek().type == TokenType.COMMA:
                    self.advance()
            self.expect(TokenType.RPAREN)
            
            return_type = None
            if self.peek().type == TokenType.ARROW:
                self.advance()
                return_type = self.parse_type()
            
            return FunctionType(params=params, return_type=return_type)
        
        # Primitive types
        if token.type == TokenType.IDENTIFIER:
            primitive_types = {'int', 'float', 'bool', 'string', 'char', 'byte', 'void'}
            if token.value in primitive_types:
                self.advance()
                return PrimitiveType(name=token.value)
            
            # Named type (user-defined)
            self.advance()
            return NamedType(name=token.value)
        
        raise ParseError(f"Unexpected token in type: {token.type.name}", token)
    
    def parse_block(self) -> Block:
        """Parse a block"""
        self.expect(TokenType.LBRACE)
        self.skip_newlines()
        
        statements = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return Block(statements=statements)
    
    def parse_statement(self) -> Optional[Statement]:
        """Parse a statement"""
        token = self.peek()
        
        if token.type == TokenType.LET or token.type == TokenType.MUT:
            return self.parse_let_statement()
        elif token.type == TokenType.RETURN:
            return self.parse_return_statement()
        elif token.type == TokenType.IF:
            return self.parse_if_statement()
        elif token.type == TokenType.WHILE:
            return self.parse_while_statement()
        elif token.type == TokenType.FOR:
            return self.parse_for_statement()
        elif token.type == TokenType.MATCH:
            return self.parse_match_statement()
        elif token.type == TokenType.SPAWN:
            return self.parse_spawn_statement()
        elif token.type == TokenType.IDENTIFIER:
            # Could be assignment or expression
            if self.peek_next().type == TokenType.ASSIGN:
                return self.parse_assignment_statement()
            elif self.peek_next().type in (TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
                                           TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.PERCENT_ASSIGN):
                return self.parse_compound_assignment()
        
        # Expression statement
        expr = self.parse_expression()
        if expr:
            return expr
        return None
    
    def parse_let_statement(self) -> LetStatement:
        """Parse let statement"""
        mutable = False
        if self.peek().type == TokenType.MUT:
            self.advance()
            mutable = True
        else:
            self.advance()  # Consume 'let'
        
        name_token = self.expect(TokenType.IDENTIFIER)
        
        type_annotation = None
        if self.peek().type == TokenType.COLON:
            self.advance()
            type_annotation = self.parse_type()
        
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        
        return LetStatement(
            name=name_token.value,
            type_annotation=type_annotation,
            value=value,
            mutable=mutable
        )
    
    def parse_assignment_statement(self) -> AssignmentStatement:
        """Parse assignment statement"""
        target = self.parse_expression()
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        
        return AssignmentStatement(target=target, value=value)
    
    def parse_compound_assignment(self) -> AssignmentStatement:
        """Parse compound assignment (+=, -=, etc.)"""
        target = self.parse_expression()
        
        op_token = self.advance()
        value = self.parse_expression()
        
        # Convert compound assignment to binary operation
        op_map = {
            TokenType.PLUS_ASSIGN: BinaryOp.ADD,
            TokenType.MINUS_ASSIGN: BinaryOp.SUB,
            TokenType.STAR_ASSIGN: BinaryOp.MUL,
            TokenType.SLASH_ASSIGN: BinaryOp.DIV,
            TokenType.PERCENT_ASSIGN: BinaryOp.MOD,
        }
        
        # Create binary expression with the operator
        binary_expr = BinaryExpression(
            op=op_map[op_token.type],
            left=target,
            right=value
        )
        
        return AssignmentStatement(target=target, value=binary_expr)
    
    def parse_return_statement(self) -> ReturnStatement:
        """Parse return statement"""
        self.expect(TokenType.RETURN)
        
        value = None
        if self.peek().type != TokenType.NEWLINE and self.peek().type != TokenType.RBRACE:
            value = self.parse_expression()
        
        return ReturnStatement(value=value)
    
    def parse_if_statement(self) -> IfStatement:
        """Parse if statement"""
        self.expect(TokenType.IF)
        condition = self.parse_expression()
        then_block = self.parse_block()
        
        else_block = None
        if self.peek().type == TokenType.ELSE:
            self.advance()
            if self.peek().type == TokenType.IF:
                else_block = self.parse_if_statement()
            else:
                else_block = self.parse_block()
        
        return IfStatement(
            condition=condition,
            then_block=then_block,
            else_block=else_block
        )
    
    def parse_while_statement(self) -> WhileStatement:
        """Parse while statement"""
        self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        body = self.parse_block()
        
        return WhileStatement(condition=condition, body=body)
    
    def parse_for_statement(self) -> ForStatement:
        """Parse for statement"""
        self.expect(TokenType.FOR)
        variable = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        iterable = self.parse_expression()
        body = self.parse_block()
        
        return ForStatement(variable=variable, iterable=iterable, body=body)
    
    def parse_match_statement(self) -> MatchStatement:
        """Parse match statement"""
        self.expect(TokenType.MATCH)
        expression = self.parse_expression()
        
        self.expect(TokenType.LBRACE)
        arms = []
        
        while self.peek().type != TokenType.RBRACE:
            pattern = self.parse_pattern()
            self.expect(TokenType.THICK_ARROW)
            
            if self.peek().type == TokenType.LBRACE:
                body = self.parse_block()
            else:
                body = self.parse_expression()
            
            arms.append(MatchArm(pattern=pattern, body=body))
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return MatchStatement(expression=expression, arms=arms)
    
    def parse_pattern(self) -> Pattern:
        """Parse a pattern"""
        token = self.peek()
        
        if token.type == TokenType.UNDERSCORE:
            self.advance()
            return WildcardPattern()
        
        if token.type == TokenType.INT:
            self.advance()
            return LiteralPattern(value=IntLiteral(value=int(token.value)))
        
        if token.type == TokenType.STRING:
            self.advance()
            return LiteralPattern(value=StringLiteral(value=token.value))
        
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            
            # Check for enum pattern
            if self.peek().type == TokenType.LPAREN:
                self.advance()
                binding = None
                if self.peek().type != TokenType.RPAREN:
                    binding = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.RPAREN)
                
                return EnumPattern(
                    enum_name="",
                    variant=token.value,
                    binding=binding
                )
            
            return IdentifierPattern(name=token.value)
        
        raise ParseError(f"Unexpected token in pattern: {token.type.name}", token)
    
    def parse_spawn_statement(self) -> SpawnStatement:
        """Parse spawn statement"""
        self.expect(TokenType.SPAWN)
        call = self.parse_function_call_expression()
        return SpawnStatement(call=call)
    
    def parse_expression(self) -> Expression:
        """Parse expression (lowest precedence)"""
        return self.parse_or_expression()
    
    def parse_or_expression(self) -> Expression:
        """Parse OR expression"""
        left = self.parse_and_expression()
        
        while self.peek().type == TokenType.OR_OR or self.peek().type == TokenType.OR:
            op_token = self.advance()
            right = self.parse_and_expression()
            
            op = BinaryOp.OR if op_token.type == TokenType.OR else BinaryOp.OR
            left = BinaryExpression(op=op, left=left, right=right)
        
        return left
    
    def parse_and_expression(self) -> Expression:
        """Parse AND expression"""
        left = self.parse_bitwise_or_expression()
        
        while self.peek().type == TokenType.AND_AND or self.peek().type == TokenType.AND:
            op_token = self.advance()
            right = self.parse_bitwise_or_expression()
            
            op = BinaryOp.AND if op_token.type == TokenType.AND else BinaryOp.AND
            left = BinaryExpression(op=op, left=left, right=right)
        
        return left
    
    def parse_bitwise_or_expression(self) -> Expression:
        """Parse bitwise OR expression"""
        left = self.parse_bitwise_xor_expression()
        
        while self.peek().type == TokenType.BIT_OR:
            self.advance()
            right = self.parse_bitwise_xor_expression()
            left = BinaryExpression(op=BinaryOp.BIT_OR, left=left, right=right)
        
        return left
    
    def parse_bitwise_xor_expression(self) -> Expression:
        """Parse bitwise XOR expression"""
        left = self.parse_bitwise_and_expression()
        
        while self.peek().type == TokenType.BIT_XOR:
            self.advance()
            right = self.parse_bitwise_and_expression()
            left = BinaryExpression(op=BinaryOp.BIT_XOR, left=left, right=right)
        
        return left
    
    def parse_bitwise_and_expression(self) -> Expression:
        """Parse bitwise AND expression"""
        left = self.parse_equality_expression()
        
        while self.peek().type == TokenType.BIT_AND:
            self.advance()
            right = self.parse_equality_expression()
            left = BinaryExpression(op=BinaryOp.BIT_AND, left=left, right=right)
        
        return left
    
    def parse_equality_expression(self) -> Expression:
        """Parse equality expression"""
        left = self.parse_relational_expression()
        
        while self.peek().type in (TokenType.EQ, TokenType.NEQ):
            op_token = self.advance()
            right = self.parse_relational_expression()
            
            op = BinaryOp.EQ if op_token.type == TokenType.EQ else BinaryOp.NEQ
            left = BinaryExpression(op=op, left=left, right=right)
        
        return left
    
    def parse_relational_expression(self) -> Expression:
        """Parse relational expression"""
        left = self.parse_shift_expression()
        
        while self.peek().type in (TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
            op_token = self.advance()
            right = self.parse_shift_expression()
            
            op_map = {
                TokenType.LT: BinaryOp.LT,
                TokenType.LTE: BinaryOp.LTE,
                TokenType.GT: BinaryOp.GT,
                TokenType.GTE: BinaryOp.GTE,
            }
            left = BinaryExpression(op=op_map[op_token.type], left=left, right=right)
        
        return left
    
    def parse_shift_expression(self) -> Expression:
        """Parse shift expression"""
        left = self.parse_additive_expression()
        
        while self.peek().type in (TokenType.SHL, TokenType.SHR):
            op_token = self.advance()
            right = self.parse_additive_expression()
            
            op = BinaryOp.SHL if op_token.type == TokenType.SHL else BinaryOp.SHR
            left = BinaryExpression(op=op, left=left, right=right)
        
        return left
    
    def parse_additive_expression(self) -> Expression:
        """Parse additive expression"""
        left = self.parse_multiplicative_expression()
        
        while self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.advance()
            right = self.parse_multiplicative_expression()
            
            op = BinaryOp.ADD if op_token.type == TokenType.PLUS else BinaryOp.SUB
            left = BinaryExpression(op=op, left=left, right=right)
        
        return left
    
    def parse_multiplicative_expression(self) -> Expression:
        """Parse multiplicative expression"""
        left = self.parse_power_expression()
        
        while self.peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_token = self.advance()
            right = self.parse_power_expression()
            
            op_map = {
                TokenType.STAR: BinaryOp.MUL,
                TokenType.SLASH: BinaryOp.DIV,
                TokenType.PERCENT: BinaryOp.MOD,
            }
            left = BinaryExpression(op=op_map[op_token.type], left=left, right=right)
        
        return left
    
    def parse_power_expression(self) -> Expression:
        """Parse power expression"""
        left = self.parse_unary_expression()
        
        if self.peek().type == TokenType.POWER:
            self.advance()
            right = self.parse_power_expression()  # Right-associative
            left = BinaryExpression(op=BinaryOp.POW, left=left, right=right)
        
        return left
    
    def parse_unary_expression(self) -> Expression:
        """Parse unary expression"""
        token = self.peek()
        
        if token.type == TokenType.MINUS:
            self.advance()
            operand = self.parse_unary_expression()
            return UnaryExpression(op=UnaryOp.NEG, operand=operand)
        
        if token.type == TokenType.NOT:
            self.advance()
            operand = self.parse_unary_expression()
            return UnaryExpression(op=UnaryOp.NOT, operand=operand)
        
        if token.type == TokenType.BIT_NOT:
            self.advance()
            operand = self.parse_unary_expression()
            return UnaryExpression(op=UnaryOp.BIT_NOT, operand=operand)
        
        if token.type == TokenType.INCREMENT:
            self.advance()
            operand = self.parse_unary_expression()
            return UnaryExpression(op=UnaryOp.INCREMENT, operand=operand)
        
        if token.type == TokenType.DECREMENT:
            self.advance()
            operand = self.parse_unary_expression()
            return UnaryExpression(op=UnaryOp.DECREMENT, operand=operand)
        
        return self.parse_postfix_expression()
    
    def parse_postfix_expression(self) -> Expression:
        """Parse postfix expression"""
        expr = self.parse_primary_expression()
        
        while True:
            if self.peek().type == TokenType.LPAREN:
                # Function call
                self.advance()
                arguments = []
                
                if self.peek().type != TokenType.RPAREN:
                    while True:
                        arguments.append(self.parse_expression())
                        if self.peek().type != TokenType.COMMA:
                            break
                        self.advance()
                
                self.expect(TokenType.RPAREN)
                expr = FunctionCall(function=expr, arguments=arguments)
            
            elif self.peek().type == TokenType.DOT:
                # Field access or method call
                self.advance()
                name_token = self.expect(TokenType.IDENTIFIER)
                
                if self.peek().type == TokenType.LPAREN:
                    # Method call
                    self.advance()
                    arguments = []
                    
                    if self.peek().type != TokenType.RPAREN:
                        while True:
                            arguments.append(self.parse_expression())
                            if self.peek().type != TokenType.COMMA:
                                break
                            self.advance()
                    
                    self.expect(TokenType.RPAREN)
                    expr = MethodCall(object=expr, method=name_token.value, arguments=arguments)
                else:
                    # Field access
                    expr = FieldAccess(object=expr, field=name_token.value)
            
            elif self.peek().type == TokenType.LBRACKET:
                # Index access
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = IndexAccess(object=expr, index=index)
            
            elif self.peek().type == TokenType.INCREMENT:
                self.advance()
                expr = UnaryExpression(op=UnaryOp.INCREMENT, operand=expr)
            
            elif self.peek().type == TokenType.DECREMENT:
                self.advance()
                expr = UnaryExpression(op=UnaryOp.DECREMENT, operand=expr)
            
            else:
                break
        
        return expr
    
    def parse_primary_expression(self) -> Expression:
        """Parse primary expression"""
        token = self.peek()
        
        if token.type == TokenType.INT:
            self.advance()
            return IntLiteral(value=int(token.value))
        
        if token.type == TokenType.FLOAT:
            self.advance()
            return FloatLiteral(value=float(token.value))
        
        if token.type == TokenType.STRING:
            self.advance()
            return StringLiteral(value=token.value)
        
        if token.type == TokenType.CHAR:
            self.advance()
            return CharLiteral(value=token.value)
        
        if token.type == TokenType.TRUE:
            self.advance()
            return BoolLiteral(value=True)
        
        if token.type == TokenType.FALSE:
            self.advance()
            return BoolLiteral(value=False)
        
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return Identifier(name=token.value)
        
        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        
        if token.type == TokenType.LBRACKET:
            # Array literal
            self.advance()
            elements = []
            
            if self.peek().type != TokenType.RBRACKET:
                while True:
                    elements.append(self.parse_expression())
                    if self.peek().type != TokenType.COMMA:
                        break
                    self.advance()
            
            self.expect(TokenType.RBRACKET)
            return FunctionCall(
                function=Identifier(name="array"),
                arguments=elements
            )
        
        if token.type == TokenType.LBRACE:
            # Map literal
            self.advance()
            # TODO: Parse map literals
            
        if token.type == TokenType.AWAIT:
            self.advance()
            operand = self.parse_expression()
            return AwaitExpression(operand=operand)
        
        raise ParseError(f"Unexpected token: {token.type.name}", token)


def parse(tokens: List[Token]) -> Program:
    """Convenience function to parse tokens"""
    parser = Parser(tokens)
    return parser.parse()
