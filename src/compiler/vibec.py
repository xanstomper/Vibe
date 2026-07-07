#!/usr/bin/env python3
"""
Vibe Compiler (vibec)

Main compiler driver for the Vibe programming language
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from lexer.lexer import tokenize, LexerError
from parser.parser import parse, ParseError
from compiler.type_checker import TypeChecker, TypeError
from codegen.c_generator import generate_c
from ai_metadata.collector import MetadataCollector, collect_metadata_from_ast


class VibeCompiler:
    """Main Vibe compiler"""
    
    def __init__(self, verbose: bool = False, emit_c: bool = False):
        self.verbose = verbose
        self.emit_c = emit_c
        self.errors = []
    
    def log(self, message: str):
        """Log a message if verbose"""
        if self.verbose:
            print(f"[vibec] {message}")
    
    def compile(self, source_file: str, output_file: str = None) -> bool:
        """Compile a Vibe source file"""
        self.errors = []
        
        # Read source
        self.log(f"Reading {source_file}")
        try:
            with open(source_file, 'r') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {source_file}")
            return False
        
        # Tokenize
        self.log("Tokenizing...")
        try:
            tokens = tokenize(source, source_file)
            self.log(f"Generated {len(tokens)} tokens")
        except LexerError as e:
            print(f"Lexer Error: {e}")
            return False
        
        # Parse
        self.log("Parsing...")
        try:
            program = parse(tokens)
            self.log("Parse successful")
        except ParseError as e:
            print(f"Parse Error: {e}")
            return False
        
        # Type check
        self.log("Type checking...")
        type_checker = TypeChecker()
        type_errors = type_checker.check_program(program)
        
        if type_errors:
            for error in type_errors:
                print(f"Type Error: {error}")
            self.errors.extend(type_errors)
            return False
        
        self.log("Type checking passed")
        
        # Collect AI metadata
        self.log("Collecting AI metadata...")
        metadata = collect_metadata_from_ast(program, source)
        self.log(f"Module: {metadata.module_name}")
        self.log(f"Intent: {', '.join(metadata.intent)}")
        
        # Generate code
        self.log("Generating code...")
        
        if self.emit_c:
            c_code = generate_c(program)
            
            if output_file is None:
                output_file = source_file.replace('.vibe', '.c')
            
            with open(output_file, 'w') as f:
                f.write(c_code)
            
            self.log(f"Generated C code: {output_file}")
        
        # Write metadata
        metadata_file = source_file.replace('.vibe', '.vibe.meta')
        collector = MetadataCollector()
        collector.project_metadata.modules[metadata.module_name] = metadata
        
        with open(metadata_file, 'w') as f:
            f.write(collector.to_vibe_metadata())
        
        self.log(f"Generated metadata: {metadata_file}")
        
        return True
    
    def compile_to_executable(self, source_file: str, output_file: str = None) -> bool:
        """Compile to executable"""
        # First compile to C
        c_file = source_file.replace('.vibe', '.c')
        if not self.compile(source_file, c_file):
            return False
        
        # Then compile C to executable
        if output_file is None:
            output_file = source_file.replace('.vibe', '')
        
        self.log(f"Compiling C to executable: {output_file}")
        
        try:
            result = subprocess.run(
                ['gcc', '-o', output_file, c_file, '-lm'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"C compilation failed:")
                print(result.stderr)
                return False
            
            self.log(f"Generated executable: {output_file}")
            return True
            
        except FileNotFoundError:
            print("Error: gcc not found. Please install gcc.")
            return False
    
    def run(self, source_file: str) -> bool:
        """Compile and run a Vibe file"""
        # Compile to executable
        exe_file = source_file.replace('.vibe', '')
        if not self.compile_to_executable(source_file, exe_file):
            return False
        
        # Run the executable
        self.log(f"Running: {exe_file}")
        
        try:
            result = subprocess.run([f'./{exe_file}'])
            return result.returncode == 0
        except KeyboardInterrupt:
            print("\nInterrupted")
            return False
        finally:
            # Clean up executable
            if os.path.exists(exe_file):
                os.remove(exe_file)
    
    def analyze(self, source_file: str) -> bool:
        """Analyze a Vibe file and generate report"""
        # Read source
        try:
            with open(source_file, 'r') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {source_file}")
            return False
        
        # Tokenize
        try:
            tokens = tokenize(source, source_file)
        except LexerError as e:
            print(f"Lexer Error: {e}")
            return False
        
        # Parse
        try:
            program = parse(tokens)
        except ParseError as e:
            print(f"Parse Error: {e}")
            return False
        
        # Collect metadata
        metadata = collect_metadata_from_ast(program, source)
        
        # Print analysis
        print(f"\n=== Vibe Analysis: {source_file} ===\n")
        print(f"Module: {metadata.module_name}")
        print(f"Intent: {', '.join(metadata.intent)}")
        print(f"Owner: {metadata.owner}")
        print(f"Risk Level: {metadata.risk.value}")
        print(f"Lines of Code: {metadata.lines_of_code}")
        print(f"Dependencies: {', '.join(metadata.dependencies)}")
        
        if metadata.public_functions:
            print(f"\nPublic Functions:")
            for func in metadata.public_functions:
                print(f"  - {func.name}: {func.signature}")
        
        if metadata.public_types:
            print(f"\nPublic Types:")
            for typ in metadata.public_types:
                print(f"  - {typ.name}: {typ.kind}")
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Vibe Compiler (vibec)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vibec build src/main.vibe          # Compile to executable
  vibec run src/main.vibe            # Compile and run
  vibec emit-c src/main.vibe         # Emit C code
  vibec analyze src/main.vibe        # Analyze code
  vibec test src/                    # Run tests
        """
    )
    
    parser.add_argument('command', 
                       choices=['build', 'run', 'emit-c', 'analyze', 'test', 'release'],
                       help='Command to execute')
    
    parser.add_argument('files', 
                       nargs='+',
                       help='Source files to process')
    
    parser.add_argument('-o', '--output',
                       help='Output file')
    
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='Verbose output')
    
    parser.add_argument('--no-type-check',
                       action='store_true',
                       help='Skip type checking')
    
    parser.add_argument('--target',
                       choices=['c', 'native'],
                       default='native',
                       help='Target platform')
    
    args = parser.parse_args()
    
    compiler = VibeCompiler(
        verbose=args.verbose,
        emit_c=(args.command == 'emit-c')
    )
    
    success = True
    
    for file in args.files:
        if args.command == 'build':
            success = compiler.compile_to_executable(file, args.output) and success
        
        elif args.command == 'run':
            success = compiler.run(file) and success
        
        elif args.command == 'emit-c':
            success = compiler.compile(file, args.output) and success
        
        elif args.command == 'analyze':
            success = compiler.analyze(file) and success
        
        elif args.command == 'test':
            # Run tests in directory
            test_dir = Path(file)
            if test_dir.is_dir():
                for test_file in test_dir.glob('*.vibe'):
                    print(f"\nTesting {test_file}...")
                    success = compiler.run(str(test_file)) and success
            else:
                success = compiler.run(file) and success
        
        elif args.command == 'release':
            # Release build with optimizations
            success = compiler.compile_to_executable(file, args.output) and success
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
