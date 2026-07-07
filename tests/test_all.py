#!/usr/bin/env python3
"""
Vibe Language Test Suite

Tests for the Vibe compiler pipeline
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lexer.lexer import tokenize, LexerError
from src.parser.parser import parse, ParseError
from src.compiler.type_checker import TypeChecker
from src.codegen.c_generator import generate_c


def test_lexer():
    """Test lexer tokenization"""
    print("Testing lexer...")
    
    # Test basic tokens
    source = "let x = 42"
    tokens = tokenize(source)
    assert len(tokens) > 0
    assert tokens[0].value == "let"
    assert tokens[1].value == "x"
    assert tokens[2].value == "="
    assert tokens[3].value == "42"
    print("  Basic tokens: PASS")
    
    # Test string literal
    source = '"hello world"'
    tokens = tokenize(source)
    assert tokens[0].value == "hello world"
    print("  String literal: PASS")
    
    # Test operators
    source = "a + b * c"
    tokens = tokenize(source)
    assert any(t.value == "+" for t in tokens)
    assert any(t.value == "*" for t in tokens)
    print("  Operators: PASS")
    
    print("Lexer tests: ALL PASS\n")


def test_parser():
    """Test parser"""
    print("Testing parser...")
    
    # Test simple program
    source = '''
module Test

func add(a: int, b: int) -> int {
    return a + b
}
'''
    tokens = tokenize(source)
    program = parse(tokens)
    
    assert program.module is not None
    assert program.module.name == "Test"
    assert len(program.declarations) == 1
    print("  Simple program: PASS")
    
    # Test struct
    source = '''
module Test

struct Point {
    x: float
    y: float
}
'''
    tokens = tokenize(source)
    program = parse(tokens)
    
    assert len(program.declarations) == 1
    decl = program.declarations[0]
    assert hasattr(decl, 'fields')
    assert len(decl.fields) == 2
    print("  Struct declaration: PASS")
    
    # Test enum
    source = '''
module Test

enum Color {
    Red
    Green
    Blue
}
'''
    tokens = tokenize(source)
    program = parse(tokens)
    
    assert len(program.declarations) == 1
    decl = program.declarations[0]
    assert hasattr(decl, 'variants')
    assert len(decl.variants) == 3
    print("  Enum declaration: PASS")
    
    print("Parser tests: ALL PASS\n")


def test_type_checker():
    """Test type checker"""
    print("Testing type checker...")
    
    source = '''
module Test

func add(a: int, b: int) -> int {
    return a + b
}

func main() -> int {
    let x = 10
    let y = 20
    let sum = add(x, y)
    return 0
}
'''
    tokens = tokenize(source)
    program = parse(tokens)
    
    checker = TypeChecker()
    errors = checker.check_program(program)
    
    # Should have no errors for valid code
    assert len(errors) == 0
    print("  Valid code: PASS")
    
    # Test type mismatch
    source = '''
module Test

func main() -> int {
    let x = "hello"
    let y = 42
    let z = x + y
    return 0
}
'''
    tokens = tokenize(source)
    program = parse(tokens)
    
    checker = TypeChecker()
    errors = checker.check_program(program)
    
    # Should have type errors
    assert len(errors) > 0
    print("  Type mismatch detection: PASS")
    
    print("Type checker tests: ALL PASS\n")


def test_code_generator():
    """Test code generator"""
    print("Testing code generator...")
    
    source = '''
module Test

func add(a: int, b: int) -> int {
    return a + b
}

func main() -> int {
    let x = 10
    let y = 20
    let sum = add(x, y)
    return sum
}
'''
    tokens = tokenize(source)
    program = parse(tokens)
    
    c_code = generate_c(program)
    
    assert "int add(int a, int b)" in c_code
    assert "return (a + b)" in c_code
    assert "int main(void)" in c_code
    print("  C code generation: PASS")
    
    # Test struct generation
    source = '''
module Test

struct Point {
    x: float
    y: float
}
'''
    tokens = tokenize(source)
    program = parse(tokens)
    
    c_code = generate_c(program)
    
    assert "typedef struct Point" in c_code
    assert "double x;" in c_code
    assert "double y;" in c_code
    print("  Struct code generation: PASS")
    
    print("Code generator tests: ALL PASS\n")


def test_full_pipeline():
    """Test complete compilation pipeline"""
    print("Testing full pipeline...")
    
    source = '''
module Calculator

intent:
    Simple calculator

func add(a: int, b: int) -> int {
    return a + b
}

func subtract(a: int, b: int) -> int {
    return a - b
}

func main() -> int {
    let x = 100
    let y = 50
    let result = add(x, subtract(x, y))
    return 0
}
'''
    # Tokenize
    tokens = tokenize(source)
    assert len(tokens) > 0
    
    # Parse
    program = parse(tokens)
    assert program.module.name == "Calculator"
    
    # Type check
    checker = TypeChecker()
    errors = checker.check_program(program)
    assert len(errors) == 0
    
    # Generate code
    c_code = generate_c(program)
    assert len(c_code) > 0
    
    print("  Full pipeline: PASS")
    print("Full pipeline tests: ALL PASS\n")


def main():
    """Run all tests"""
    print("=" * 50)
    print("Vibe Language Test Suite")
    print("=" * 50 + "\n")
    
    test_lexer()
    test_parser()
    test_type_checker()
    test_code_generator()
    test_full_pipeline()
    
    print("=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)


if __name__ == '__main__':
    main()
