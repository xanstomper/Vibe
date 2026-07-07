"""
Vibe Code Generator

Generates target code from AST
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CodeGenContext:
    """Code generation context"""
    indent_level: int = 0
    output: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    types: Dict[str, str] = field(default_factory=dict)
    includes: List[str] = field(default_factory=list)
    
    def indent(self):
        """Increase indent"""
        self.indent_level += 1
    
    def dedent(self):
        """Decrease indent"""
        self.indent_level -= 1
    
    def get_indent(self) -> str:
        """Get current indentation"""
        return "    " * self.indent_level
    
    def emit(self, code: str):
        """Emit code with indentation"""
        self.output.append(f"{self.get_indent()}{code}")
    
    def emit_raw(self, code: str):
        """Emit code without indentation"""
        self.output.append(code)
    
    def emit_line(self, code: str):
        """Emit a line of code"""
        self.emit(code + "\n")
    
    def emit_blank_line(self):
        """Emit a blank line"""
        self.output.append("\n")


class CodeGenerator:
    """Vibe code generator (targets C)"""
    
    def __init__(self):
        self.context = CodeGenContext()
    
    def generate(self, program) -> str:
        """Generate C code from Vibe AST"""
        self.context = CodeGenContext()
        
        # Emit includes
        self.context.includes.append("#include <stdio.h>")
        self.context.includes.append("#include <stdlib.h>")
        self.context.includes.append("#include <string.h>")
        self.context.includes.append("#include <stdbool.h>")
        
        for include in self.context.includes:
            self.context.emit_line(include)
        
        self.context.emit_blank_line()
        
        # Forward declarations
        self.emit_forward_declarations(program)
        
        # Type definitions
        self.emit_type_definitions(program)
        
        # Function implementations
        self.emit_function_implementations(program)
        
        # Main function
        self.emit_main_function(program)
        
        return "".join(self.context.output)
    
    def emit_forward_declarations(self, program):
        """Emit forward declarations"""
        for decl in program.declarations:
            if hasattr(decl, 'name') and hasattr(decl, 'body'):
                # Function or procedure
                return_type = "void"
                if hasattr(decl, 'return_type') and decl.return_type:
                    return_type = self.get_c_type(decl.return_type)
                
                params = []
                if hasattr(decl, 'parameters'):
                    for param in decl.parameters:
                        param_type = self.get_c_type(param.type_annotation)
                        params.append(f"{param_type} {param.name}")
                
                params_str = ", ".join(params) if params else "void"
                self.context.emit_line(f"{return_type} {decl.name}({params_str});")
        
        self.context.emit_blank_line()
    
    def emit_type_definitions(self, program):
        """Emit struct and enum definitions"""
        for decl in program.declarations:
            if hasattr(decl, 'name'):
                # Struct
                if hasattr(decl, 'fields'):
                    self.emit_struct_definition(decl)
                # Enum
                elif hasattr(decl, 'variants'):
                    self.emit_enum_definition(decl)
        
        self.context.emit_blank_line()
    
    def emit_struct_definition(self, struct):
        """Emit a struct definition"""
        self.context.emit_line(f"typedef struct {struct.name} {{")
        self.context.indent()
        
        for field in struct.fields:
            field_type = self.get_c_type(field.type_annotation)
            self.context.emit_line(f"{field_type} {field.name};")
        
        self.context.dedent()
        self.context.emit_line(f"}} {struct.name};")
        self.context.emit_blank_line()
    
    def emit_enum_definition(self, enum):
        """Emit an enum definition"""
        self.context.emit_line(f"typedef enum {enum.name} {{")
        self.context.indent()
        
        for i, variant in enumerate(enum.variants):
            comma = "," if i < len(enum.variants) - 1 else ""
            self.context.emit_line(f"{enum.name}_{variant.name}{comma}")
        
        self.context.dedent()
        self.context.emit_line(f"}} {enum.name};")
        self.context.emit_blank_line()
    
    def emit_function_implementations(self, program):
        """Emit function implementations"""
        for decl in program.declarations:
            if hasattr(decl, 'body') and decl.body:
                self.emit_function(decl)
    
    def emit_function(self, func):
        """Emit a function implementation"""
        # Return type
        return_type = "void"
        if hasattr(func, 'return_type') and func.return_type:
            return_type = self.get_c_type(func.return_type)
        
        # Parameters
        params = []
        if hasattr(func, 'parameters'):
            for param in func.parameters:
                param_type = self.get_c_type(param.type_annotation)
                params.append(f"{param_type} {param.name}")
        
        params_str = ", ".join(params) if params else "void"
        
        # Function header
        self.context.emit_line(f"{return_type} {func.name}({params_str}) {{")
        self.context.indent()
        
        # Function body
        if func.body:
            for stmt in func.body.statements:
                self.emit_statement(stmt)
        
        self.context.dedent()
        self.context.emit_line("}")
        self.context.emit_blank_line()
    
    def emit_main_function(self, program):
        """Emit main function"""
        # Find main function or create one
        main_func = None
        for decl in program.declarations:
            if hasattr(decl, 'name') and decl.name == "main":
                main_func = decl
                break
        
        if main_func:
            self.emit_function(main_func)
        else:
            # Generate minimal main
            self.context.emit_line("int main(void) {")
            self.context.indent()
            self.context.emit_line("return 0;")
            self.context.dedent()
            self.context.emit_line("}")
    
    def emit_statement(self, stmt):
        """Emit a statement"""
        stmt_type = stmt.node_type.value if hasattr(stmt, 'node_type') else str(stmt)
        
        if stmt_type == "let":
            self.emit_let_statement(stmt)
        elif stmt_type == "assignment":
            self.emit_assignment(stmt)
        elif stmt_type == "return":
            self.emit_return(stmt)
        elif stmt_type == "if":
            self.emit_if(stmt)
        elif stmt_type == "while":
            self.emit_while(stmt)
        elif stmt_type == "for":
            self.emit_for(stmt)
        elif stmt_type == "spawn":
            self.emit_spawn(stmt)
        elif hasattr(stmt, 'node_type'):
            # Expression statement
            expr = self.emit_expression(stmt)
            self.context.emit_line(f"{expr};")
    
    def emit_let_statement(self, stmt):
        """Emit a let statement"""
        var_type = "auto"
        if stmt.type_annotation:
            var_type = self.get_c_type(stmt.type_annotation)
        
        value = self.emit_expression(stmt.value)
        
        if stmt.mutable:
            self.context.emit_line(f"{var_type} {stmt.name} = {value};")
        else:
            # In C, we don't have immutability, but we can use const
            self.context.emit_line(f"const {var_type} {stmt.name} = {value};")
    
    def emit_assignment(self, stmt):
        """Emit an assignment"""
        target = self.emit_expression(stmt.target)
        value = self.emit_expression(stmt.value)
        self.context.emit_line(f"{target} = {value};")
    
    def emit_return(self, stmt):
        """Emit a return statement"""
        if stmt.value:
            value = self.emit_expression(stmt.value)
            self.context.emit_line(f"return {value};")
        else:
            self.context.emit_line("return;")
    
    def emit_if(self, stmt):
        """Emit an if statement"""
        condition = self.emit_expression(stmt.condition)
        self.context.emit_line(f"if ({condition}) {{")
        self.context.indent()
        
        for s in stmt.then_block.statements:
            self.emit_statement(s)
        
        self.context.dedent()
        
        if stmt.else_block:
            if hasattr(stmt.else_block, 'statements'):
                self.context.emit_line("} else {")
                self.context.indent()
                for s in stmt.else_block.statements:
                    self.emit_statement(s)
                self.context.dedent()
            else:
                self.context.emit_line("} else ")
                self.emit_if(stmt.else_block)
                return
        
        self.context.emit_line("}")
    
    def emit_while(self, stmt):
        """Emit a while loop"""
        condition = self.emit_expression(stmt.condition)
        self.context.emit_line(f"while ({condition}) {{")
        self.context.indent()
        
        for s in stmt.body.statements:
            self.emit_statement(s)
        
        self.context.dedent()
        self.context.emit_line("}")
    
    def emit_for(self, stmt):
        """Emit a for loop"""
        # Simplified: generate a while loop
        iterable = self.emit_expression(stmt.iterable)
        
        # Generate array iteration
        self.context.emit_line(f"for (int i = 0; i < len({iterable}); i++) {{")
        self.context.indent()
        self.context.emit_line(f"{stmt.variable} = {iterable}[i];")
        
        for s in stmt.body.statements:
            self.emit_statement(s)
        
        self.context.dedent()
        self.context.emit_line("}")
    
    def emit_spawn(self, stmt):
        """Emit a spawn statement (simplified to function call)"""
        call = self.emit_expression(stmt.call)
        self.context.emit_line(f"// spawn: {call}")
        self.context.emit_line(f"{call};")
    
    def emit_expression(self, expr) -> str:
        """Emit an expression and return the code string"""
        expr_type = expr.node_type.value if hasattr(expr, 'node_type') else str(expr)
        
        if expr_type == "int_literal":
            return str(expr.value)
        
        elif expr_type == "float_literal":
            return str(expr.value)
        
        elif expr_type == "string_literal":
            return f'"{expr.value}"'
        
        elif expr_type == "bool_literal":
            return "true" if expr.value else "false"
        
        elif expr_type == "char_literal":
            return f"'{expr.value}'"
        
        elif expr_type == "identifier":
            return expr.name
        
        elif expr_type == "binary_operation":
            left = self.emit_expression(expr.left)
            right = self.emit_expression(expr.right)
            op = expr.op.value
            return f"({left} {op} {right})"
        
        elif expr_type == "unary_operation":
            operand = self.emit_expression(expr.operand)
            op = expr.op.value
            return f"({op}{operand})"
        
        elif expr_type == "function_call":
            func = self.emit_expression(expr.function)
            args = [self.emit_expression(arg) for arg in expr.arguments]
            args_str = ", ".join(args)
            return f"{func}({args_str})"
        
        elif expr_type == "method_call":
            obj = self.emit_expression(expr.object)
            args = [self.emit_expression(arg) for arg in expr.arguments]
            args_str = ", ".join(args)
            return f"{obj}.{expr.method}({args_str})"
        
        elif expr_type == "index_access":
            obj = self.emit_expression(expr.object)
            index = self.emit_expression(expr.index)
            return f"{obj}[{index}]"
        
        elif expr_type == "field_access":
            obj = self.emit_expression(expr.object)
            return f"{obj}.{expr.field}"
        
        elif expr_type == "await":
            # Simplified: just evaluate the expression
            return self.emit_expression(expr.operand)
        
        return "/* unknown expression */"
    
    def get_c_type(self, type_node) -> str:
        """Convert Vibe type to C type"""
        if type_node is None:
            return "void"
        
        node_type = type_node.node_type.value if hasattr(type_node, 'node_type') else str(type_node)
        
        if node_type == "primitive_type":
            type_map = {
                "int": "int",
                "float": "double",
                "bool": "bool",
                "string": "const char*",
                "char": "char",
                "byte": "unsigned char",
                "void": "void",
            }
            return type_map.get(type_node.name, "void")
        
        elif node_type == "array_type":
            element_type = self.get_c_type(type_node.element_type)
            return f"{element_type}*"
        
        elif node_type == "map_type":
            # Simplified: use void* for now
            return "void*"
        
        elif node_type == "optional_type":
            inner_type = self.get_c_type(type_node.inner_type)
            return f"{inner_type}*"
        
        elif node_type == "result_type":
            # Simplified: use int for result codes
            return "int"
        
        elif node_type == "named_type":
            return type_node.name
        
        return "void"


def generate_c(program) -> str:
    """Convenience function to generate C code"""
    generator = CodeGenerator()
    return generator.generate(program)
