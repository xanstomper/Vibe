"""
Vibe Type Checker

Validates types and enforces type safety
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class TypeError(Exception):
    """Type checking error"""
    def __init__(self, message: str, location=None):
        self.message = message
        self.location = location
        super().__init__(message)


class TypeKind(Enum):
    """Type kinds"""
    PRIMITIVE = "primitive"
    STRUCT = "struct"
    ENUM = "enum"
    TRAIT = "trait"
    FUNCTION = "function"
    ARRAY = "array"
    MAP = "map"
    OPTIONAL = "optional"
    RESULT = "result"
    GENERIC = "generic"
    UNKNOWN = "unknown"


@dataclass
class TypeInfo:
    """Type information"""
    kind: TypeKind
    name: str
    base_type: Optional['TypeInfo'] = None  # For containers
    key_type: Optional['TypeInfo'] = None  # For maps
    value_type: Optional['TypeInfo'] = None  # For maps
    return_type: Optional['TypeInfo'] = None  # For functions
    param_types: List['TypeInfo'] = None  # For functions
    fields: Dict[str, 'TypeInfo'] = None  # For structs
    variants: Dict[str, List['TypeInfo']] = None  # For enums
    is_mutable: bool = False
    is_nullable: bool = False
    
    def __post_init__(self):
        if self.param_types is None:
            self.param_types = []
        if self.fields is None:
            self.fields = {}
        if self.variants is None:
            self.variants = {}
    
    def __eq__(self, other):
        if not isinstance(other, TypeInfo):
            return False
        if self.kind != other.kind:
            return False
        if self.name != other.name:
            return False
        if self.kind == TypeKind.ARRAY:
            return self.base_type == other.base_type
        if self.kind == TypeKind.MAP:
            return self.key_type == other.key_type and self.value_type == other.value_type
        if self.kind == TypeKind.OPTIONAL:
            return self.base_type == other.base_type
        if self.kind == TypeKind.FUNCTION:
            return (self.param_types == other.param_types and 
                    self.return_type == other.return_type)
        return True
    
    def is_compatible_with(self, other: 'TypeInfo') -> bool:
        """Check if this type is compatible with another"""
        if self == other:
            return True
        
        # Optional compatibility
        if self.kind == TypeKind.OPTIONAL:
            return self.base_type.is_compatible_with(other)
        if other.kind == TypeKind.OPTIONAL:
            return self.is_compatible_with(other.base_type)
        
        # Result compatibility
        if self.kind == TypeKind.RESULT:
            return self.base_type.is_compatible_with(other)
        if other.kind == TypeKind.RESULT:
            return self.is_compatible_with(other.base_type)
        
        return False


# Built-in types
INT_TYPE = TypeInfo(kind=TypeKind.PRIMITIVE, name="int")
FLOAT_TYPE = TypeInfo(kind=TypeKind.PRIMITIVE, name="float")
BOOL_TYPE = TypeInfo(kind=TypeKind.PRIMITIVE, name="bool")
STRING_TYPE = TypeInfo(kind=TypeKind.PRIMITIVE, name="string")
CHAR_TYPE = TypeInfo(kind=TypeKind.PRIMITIVE, name="char")
BYTE_TYPE = TypeInfo(kind=TypeKind.PRIMITIVE, name="byte")
VOID_TYPE = TypeInfo(kind=TypeKind.PRIMITIVE, name="void")


class SymbolTable:
    """Symbol table for type checking"""
    
    def __init__(self):
        self.scopes: List[Dict[str, TypeInfo]] = [{}]
    
    def push_scope(self):
        """Push a new scope"""
        self.scopes.append({})
    
    def pop_scope(self):
        """Pop current scope"""
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def define(self, name: str, type_info: TypeInfo):
        """Define a symbol in current scope"""
        self.scopes[-1][name] = type_info
    
    def lookup(self, name: str) -> Optional[TypeInfo]:
        """Look up a symbol"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None
    
    def update(self, name: str, type_info: TypeInfo):
        """Update an existing symbol"""
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = type_info
                return
        raise TypeError(f"Symbol '{name}' not found")


class TypeChecker:
    """Vibe type checker"""
    
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[TypeError] = []
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[TypeInfo] = None
        
        # Register built-in functions
        self.register_builtins()
    
    def register_builtins(self):
        """Register built-in functions and types"""
        # Built-in functions
        self.symbol_table.define("print", TypeInfo(
            kind=TypeKind.FUNCTION,
            name="print",
            param_types=[STRING_TYPE],
            return_type=VOID_TYPE
        ))
        
        self.symbol_table.define("println", TypeInfo(
            kind=TypeKind.FUNCTION,
            name="println",
            param_types=[STRING_TYPE],
            return_type=VOID_TYPE
        ))
        
        self.symbol_table.define("len", TypeInfo(
            kind=TypeKind.FUNCTION,
            name="len",
            param_types=[],  # Generic
            return_type=INT_TYPE
        ))
        
        self.symbol_table.define("to_string", TypeInfo(
            kind=TypeKind.FUNCTION,
            name="to_string",
            param_types=[],  # Generic
            return_type=STRING_TYPE
        ))
        
        self.symbol_table.define("to_int", TypeInfo(
            kind=TypeKind.FUNCTION,
            name="to_int",
            param_types=[STRING_TYPE],
            return_type=INT_TYPE
        ))
        
        self.symbol_table.define("to_float", TypeInfo(
            kind=TypeKind.FUNCTION,
            name="to_float",
            param_types=[STRING_TYPE],
            return_type=FLOAT_TYPE
        ))
    
    def error(self, message: str, location=None):
        """Record a type error"""
        error = TypeError(message, location)
        self.errors.append(error)
    
    def check_program(self, program) -> List[TypeError]:
        """Type check an entire program"""
        self.errors = []
        
        # First pass: collect type and function declarations
        for decl in program.declarations:
            if hasattr(decl, 'name'):
                if hasattr(decl, 'fields'):  # Struct
                    self.register_struct(decl)
                elif hasattr(decl, 'variants'):  # Enum
                    self.register_enum(decl)
                elif hasattr(decl, 'methods'):  # Trait
                    self.register_trait(decl)
                elif hasattr(decl, 'parameters'):  # Function/Proc
                    self.register_function(decl)
        
        # Second pass: check functions
        for decl in program.declarations:
            if hasattr(decl, 'body') and decl.body:
                self.check_function(decl)
        
        return self.errors
    
    def register_struct(self, struct_decl):
        """Register a struct type"""
        fields = {}
        for field in struct_decl.fields:
            field_type = self.resolve_type(field.type_annotation)
            fields[field.name] = field_type
        
        type_info = TypeInfo(
            kind=TypeKind.STRUCT,
            name=struct_decl.name,
            fields=fields
        )
        
        self.symbol_table.define(struct_decl.name, type_info)
    
    def register_enum(self, enum_decl):
        """Register an enum type"""
        variants = {}
        for variant in enum_decl.variants:
            if variant.data:
                variant_types = [self.resolve_type(t) for t in variant.data]
                variants[variant.name] = variant_types
            else:
                variants[variant.name] = []
        
        type_info = TypeInfo(
            kind=TypeKind.ENUM,
            name=enum_decl.name,
            variants=variants
        )
        
        self.symbol_table.define(enum_decl.name, type_info)
    
    def register_trait(self, trait_decl):
        """Register a trait type"""
        methods = {}
        for method in trait_decl.methods:
            param_types = [self.resolve_type(p.type_annotation) for p in method.parameters]
            return_type = self.resolve_type(method.return_type) if method.return_type else VOID_TYPE
            
            methods[method.name] = TypeInfo(
                kind=TypeKind.FUNCTION,
                name=method.name,
                param_types=param_types,
                return_type=return_type
            )
        
        type_info = TypeInfo(
            kind=TypeKind.TRAIT,
            name=trait_decl.name,
            fields=methods  # Reusing fields for methods
        )
        
        self.symbol_table.define(trait_decl.name, type_info)
    
    def register_function(self, func_decl):
        """Register a function"""
        param_types = [self.resolve_type(p.type_annotation) for p in func_decl.parameters]
        return_type = self.resolve_type(func_decl.return_type) if func_decl.return_type else VOID_TYPE
        
        type_info = TypeInfo(
            kind=TypeKind.FUNCTION,
            name=func_decl.name,
            param_types=param_types,
            return_type=return_type
        )
        
        self.symbol_table.define(func_decl.name, type_info)
    
    def resolve_type(self, type_node) -> TypeInfo:
        """Resolve a type node to TypeInfo"""
        if type_node is None:
            return VOID_TYPE
        
        node_type = type_node.node_type.value if hasattr(type_node, 'node_type') else str(type_node)
        
        if node_type == "primitive_type":
            primitive_map = {
                "int": INT_TYPE,
                "float": FLOAT_TYPE,
                "bool": BOOL_TYPE,
                "string": STRING_TYPE,
                "char": CHAR_TYPE,
                "byte": BYTE_TYPE,
                "void": VOID_TYPE,
            }
            return primitive_map.get(type_node.name, TypeInfo(kind=TypeKind.UNKNOWN, name=type_node.name))
        
        elif node_type == "array_type":
            element_type = self.resolve_type(type_node.element_type)
            return TypeInfo(
                kind=TypeKind.ARRAY,
                name=f"[{element_type.name}]",
                base_type=element_type
            )
        
        elif node_type == "map_type":
            key_type = self.resolve_type(type_node.key_type)
            value_type = self.resolve_type(type_node.value_type)
            return TypeInfo(
                kind=TypeKind.MAP,
                name=f"{{{key_type.name}: {value_type.name}}}",
                key_type=key_type,
                value_type=value_type
            )
        
        elif node_type == "optional_type":
            inner_type = self.resolve_type(type_node.inner_type)
            return TypeInfo(
                kind=TypeKind.OPTIONAL,
                name=f"?{inner_type.name}",
                base_type=inner_type,
                is_nullable=True
            )
        
        elif node_type == "result_type":
            inner_type = self.resolve_type(type_node.inner_type)
            return TypeInfo(
                kind=TypeKind.RESULT,
                name=f"!{inner_type.name}",
                base_type=inner_type
            )
        
        elif node_type == "named_type":
            existing = self.symbol_table.lookup(type_node.name)
            if existing:
                return existing
            return TypeInfo(kind=TypeKind.UNKNOWN, name=type_node.name)
        
        elif node_type == "function_type":
            param_types = [self.resolve_type(p) for p in type_node.params]
            return_type = self.resolve_type(type_node.return_type) if type_node.return_type else VOID_TYPE
            return TypeInfo(
                kind=TypeKind.FUNCTION,
                name="function",
                param_types=param_types,
                return_type=return_type
            )
        
        return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
    
    def check_function(self, func_decl):
        """Check a function declaration"""
        self.current_function = func_decl.name
        self.current_return_type = self.resolve_type(func_decl.return_type) if func_decl.return_type else VOID_TYPE
        
        # Push new scope for function parameters
        self.symbol_table.push_scope()
        
        # Add parameters to scope
        for param in func_decl.parameters:
            param_type = self.resolve_type(param.type_annotation)
            self.symbol_table.define(param.name, param_type)
        
        # Check function body
        if func_decl.body:
            self.check_block(func_decl.body)
        
        self.symbol_table.pop_scope()
        self.current_function = None
        self.current_return_type = None
    
    def check_block(self, block):
        """Check a block of statements"""
        self.symbol_table.push_scope()
        
        for stmt in block.statements:
            self.check_statement(stmt)
        
        self.symbol_table.pop_scope()
    
    def check_statement(self, stmt):
        """Check a statement"""
        stmt_type = stmt.node_type.value if hasattr(stmt, 'node_type') else str(stmt)
        
        if stmt_type == "let":
            self.check_let_statement(stmt)
        elif stmt_type == "assignment":
            self.check_assignment(stmt)
        elif stmt_type == "return":
            self.check_return_statement(stmt)
        elif stmt_type == "if":
            self.check_if_statement(stmt)
        elif stmt_type == "while":
            self.check_while_statement(stmt)
        elif stmt_type == "for":
            self.check_for_statement(stmt)
        elif stmt_type == "match":
            self.check_match_statement(stmt)
        elif stmt_type == "spawn":
            self.check_spawn_statement(stmt)
        elif hasattr(stmt, 'node_type'):
            # Expression statement
            self.check_expression(stmt)
    
    def check_let_statement(self, stmt):
        """Check a let statement"""
        value_type = self.check_expression(stmt.value)
        
        if stmt.type_annotation:
            declared_type = self.resolve_type(stmt.type_annotation)
            if not value_type.is_compatible_with(declared_type):
                self.error(f"Type mismatch: expected {declared_type.name}, got {value_type.name}")
        
        self.symbol_table.define(stmt.name, value_type)
    
    def check_assignment(self, stmt):
        """Check an assignment statement"""
        target_type = self.check_expression(stmt.target)
        value_type = self.check_expression(stmt.value)
        
        if not value_type.is_compatible_with(target_type):
            self.error(f"Type mismatch in assignment: expected {target_type.name}, got {value_type.name}")
    
    def check_return_statement(self, stmt):
        """Check a return statement"""
        if stmt.value:
            value_type = self.check_expression(stmt.value)
            if self.current_return_type and not value_type.is_compatible_with(self.current_return_type):
                self.error(f"Return type mismatch: expected {self.current_return_type.name}, got {value_type.name}")
        elif self.current_return_type and self.current_return_type != VOID_TYPE:
            self.error("Function must return a value")
    
    def check_if_statement(self, stmt):
        """Check an if statement"""
        condition_type = self.check_expression(stmt.condition)
        
        if condition_type != BOOL_TYPE:
            self.error(f"Condition must be bool, got {condition_type.name}")
        
        self.check_block(stmt.then_block)
        
        if stmt.else_block:
            if hasattr(stmt.else_block, 'statements'):
                self.check_block(stmt.else_block)
            else:
                self.check_if_statement(stmt.else_block)
    
    def check_while_statement(self, stmt):
        """Check a while statement"""
        condition_type = self.check_expression(stmt.condition)
        
        if condition_type != BOOL_TYPE:
            self.error(f"Condition must be bool, got {condition_type.name}")
        
        self.check_block(stmt.body)
    
    def check_for_statement(self, stmt):
        """Check a for statement"""
        iterable_type = self.check_expression(stmt.iterable)
        
        if iterable_type.kind == TypeKind.ARRAY:
            self.symbol_table.define(stmt.variable, iterable_type.base_type)
        elif iterable_type.kind == TypeKind.MAP:
            self.symbol_table.define(stmt.variable, iterable_type.key_type)
        else:
            self.error(f"Cannot iterate over {iterable_type.name}")
        
        self.check_block(stmt.body)
    
    def check_match_statement(self, stmt):
        """Check a match statement"""
        expr_type = self.check_expression(stmt.expression)
        
        for arm in stmt.arms:
            # Check pattern
            self.check_pattern(arm.pattern, expr_type)
            
            # Check arm body
            if hasattr(arm.body, 'statements'):
                self.check_block(arm.body)
            else:
                self.check_expression(arm.body)
    
    def check_pattern(self, pattern, expected_type):
        """Check a pattern against expected type"""
        pattern_type = pattern.node_type if hasattr(pattern, 'node_type') else str(pattern)
        
        if pattern_type == "wildcard":
            return
        
        if pattern_type == "literal":
            literal_type = self.check_expression(pattern.value)
            if not literal_type.is_compatible_with(expected_type):
                self.error(f"Pattern type mismatch: expected {expected_type.name}, got {literal_type.name}")
        
        elif pattern_type == "identifier":
            self.symbol_table.define(pattern.name, expected_type)
        
        elif pattern_type == "enum":
            if expected_type.kind != TypeKind.ENUM:
                self.error(f"Cannot match enum pattern on non-enum type {expected_type.name}")
                return
            
            if pattern.variant not in expected_type.variants:
                self.error(f"Unknown enum variant: {pattern.variant}")
                return
            
            variant_types = expected_type.variants[pattern.variant]
            if pattern.binding and variant_types:
                # Create tuple type for variant data
                if len(variant_types) == 1:
                    self.symbol_table.define(pattern.binding, variant_types[0])
                # TODO: Handle multi-data variants
    
    def check_spawn_statement(self, stmt):
        """Check a spawn statement"""
        self.check_expression(stmt.call)
    
    def check_expression(self, expr) -> TypeInfo:
        """Check an expression and return its type"""
        expr_type = expr.node_type.value if hasattr(expr, 'node_type') else str(expr)
        
        if expr_type == "int_literal":
            return INT_TYPE
        
        elif expr_type == "float_literal":
            return FLOAT_TYPE
        
        elif expr_type == "string_literal":
            return STRING_TYPE
        
        elif expr_type == "bool_literal":
            return BOOL_TYPE
        
        elif expr_type == "char_literal":
            return CHAR_TYPE
        
        elif expr_type == "identifier":
            type_info = self.symbol_table.lookup(expr.name)
            if type_info is None:
                self.error(f"Undefined variable: {expr.name}")
                return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
            return type_info
        
        elif expr_type == "binary_operation":
            return self.check_binary_expression(expr)
        
        elif expr_type == "unary_operation":
            return self.check_unary_expression(expr)
        
        elif expr_type == "function_call":
            return self.check_function_call(expr)
        
        elif expr_type == "method_call":
            return self.check_method_call(expr)
        
        elif expr_type == "index_access":
            return self.check_index_access(expr)
        
        elif expr_type == "field_access":
            return self.check_field_access(expr)
        
        elif expr_type == "await":
            return self.check_await_expression(expr)
        
        return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
    
    def check_binary_expression(self, expr) -> TypeInfo:
        """Check a binary expression"""
        left_type = self.check_expression(expr.left)
        right_type = self.check_expression(expr.right)
        
        op = expr.op
        
        # Arithmetic operations
        if op.value in ('+', '-', '*', '/', '%', '**'):
            if left_type == INT_TYPE and right_type == INT_TYPE:
                return INT_TYPE
            elif left_type == FLOAT_TYPE and right_type == FLOAT_TYPE:
                return FLOAT_TYPE
            elif left_type == INT_TYPE and right_type == FLOAT_TYPE:
                return FLOAT_TYPE
            elif left_type == FLOAT_TYPE and right_type == INT_TYPE:
                return FLOAT_TYPE
            elif op.value == '+' and left_type == STRING_TYPE and right_type == STRING_TYPE:
                return STRING_TYPE
            else:
                self.error(f"Cannot apply {op.value} to {left_type.name} and {right_type.name}")
                return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
        
        # Comparison operations
        if op.value in ('==', '!=', '<', '<=', '>', '>='):
            if left_type.is_compatible_with(right_type):
                return BOOL_TYPE
            else:
                self.error(f"Cannot compare {left_type.name} and {right_type.name}")
                return BOOL_TYPE
        
        # Logical operations
        if op.value in ('&&', '||'):
            if left_type == BOOL_TYPE and right_type == BOOL_TYPE:
                return BOOL_TYPE
            else:
                self.error(f"Logical operations require bool operands, got {left_type.name} and {right_type.name}")
                return BOOL_TYPE
        
        # Bitwise operations
        if op.value in ('&', '|', '^', '<<', '>>'):
            if left_type == INT_TYPE and right_type == INT_TYPE:
                return INT_TYPE
            else:
                self.error(f"Bitwise operations require int operands, got {left_type.name} and {right_type.name}")
                return INT_TYPE
        
        return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
    
    def check_unary_expression(self, expr) -> TypeInfo:
        """Check a unary expression"""
        operand_type = self.check_expression(expr.operand)
        
        op = expr.op
        
        if op.value == '-':
            if operand_type in (INT_TYPE, FLOAT_TYPE):
                return operand_type
            else:
                self.error(f"Cannot negate {operand_type.name}")
                return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
        
        if op.value == '!':
            if operand_type == BOOL_TYPE:
                return BOOL_TYPE
            else:
                self.error(f"Logical not requires bool operand, got {operand_type.name}")
                return BOOL_TYPE
        
        if op.value == '~':
            if operand_type == INT_TYPE:
                return INT_TYPE
            else:
                self.error(f"Bitwise not requires int operand, got {operand_type.name}")
                return INT_TYPE
        
        return operand_type
    
    def check_function_call(self, expr) -> TypeInfo:
        """Check a function call"""
        func_type = self.check_expression(expr.function)
        
        if func_type.kind != TypeKind.FUNCTION:
            self.error(f"Cannot call non-function {func_type.name}")
            return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
        
        # Check argument count
        if len(expr.arguments) != len(func_type.param_types):
            self.error(f"Expected {len(func_type.param_types)} arguments, got {len(expr.arguments)}")
            return func_type.return_type or VOID_TYPE
        
        # Check argument types
        for i, (arg, expected_type) in enumerate(zip(expr.arguments, func_type.param_types)):
            arg_type = self.check_expression(arg)
            if not arg_type.is_compatible_with(expected_type):
                self.error(f"Argument {i+1} type mismatch: expected {expected_type.name}, got {arg_type.name}")
        
        return func_type.return_type or VOID_TYPE
    
    def check_method_call(self, expr) -> TypeInfo:
        """Check a method call"""
        object_type = self.check_expression(expr.object)
        
        # Find method in type
        if object_type.kind == TypeKind.STRUCT:
            if expr.method in object_type.fields:
                method_type = object_type.fields[expr.method]
                if method_type.kind == TypeKind.FUNCTION:
                    return method_type.return_type or VOID_TYPE
        
        elif object_type.kind == TypeKind.TRAIT:
            if expr.method in object_type.fields:
                method_type = object_type.fields[expr.method]
                return method_type.return_type or VOID_TYPE
        
        self.error(f"Method {expr.method} not found on {object_type.name}")
        return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
    
    def check_index_access(self, expr) -> TypeInfo:
        """Check an index access"""
        object_type = self.check_expression(expr.object)
        index_type = self.check_expression(expr.index)
        
        if object_type.kind == TypeKind.ARRAY:
            if index_type != INT_TYPE:
                self.error(f"Array index must be int, got {index_type.name}")
            return object_type.base_type
        
        elif object_type.kind == TypeKind.MAP:
            if not index_type.is_compatible_with(object_type.key_type):
                self.error(f"Map key type mismatch: expected {object_type.key_type.name}, got {index_type.name}")
            return object_type.value_type
        
        self.error(f"Cannot index {object_type.name}")
        return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
    
    def check_field_access(self, expr) -> TypeInfo:
        """Check a field access"""
        object_type = self.check_expression(expr.object)
        
        if object_type.kind == TypeKind.STRUCT:
            if expr.field in object_type.fields:
                return object_type.fields[expr.field]
            self.error(f"Field {expr.field} not found in {object_type.name}")
        
        elif object_type.kind == TypeKind.TRAIT:
            if expr.field in object_type.fields:
                return object_type.fields[expr.field]
            self.error(f"Method {expr.field} not found in trait {object_type.name}")
        
        else:
            self.error(f"Cannot access field on {object_type.name}")
        
        return TypeInfo(kind=TypeKind.UNKNOWN, name="unknown")
    
    def check_await_expression(self, expr) -> TypeInfo:
        """Check an await expression"""
        operand_type = self.check_expression(expr.operand)
        
        # For now, just return the operand type
        # In a full implementation, this would check for async context
        return operand_type
