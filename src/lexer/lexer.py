"""
Vibe Language Lexer

Tokenizes Vibe source into a flat token list.
Keywords: entity, action, proc, flow, when, otherwise, loop, match,
          spawn, await, trait, return, yield, goal, constraint, guarantee,
          unsafe, owned, borrowed, let, var, and, or, not, import, from, module
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional
import re


class TT(Enum):
    """Token types"""
    # Literals
    INT = auto(); FLOAT = auto(); TEXT = auto()
    BOOL = auto(); BYTE = auto(); NONE = auto()
    # Identifiers / Keywords
    IDENT = auto()
    # Keywords (one-way: no ambiguity)
    MODULE = auto(); IMPORT = auto(); FROM = auto()
    ENTITY = auto(); PROPERTY = auto(); ACTION = auto()
    PROC = auto(); FLOW = auto(); STEP = auto()
    WHEN = auto(); OTHERWISE = auto(); LOOP = auto()
    MATCH = auto(); RETURN = auto(); YIELD = auto()
    SPAWN = auto(); AWAIT = auto(); CHANNEL = auto()
    TRAIT = auto(); IMPLEMENT = auto()
    GOAL = auto(); CONSTRAINT = auto(); GUARANTEE = auto()
    UNSAFE = auto(); OWNED = auto(); BORROWED = auto()
    LET = auto(); VAR = auto()
    # Type keywords
    TEXT = auto(); INT_TYPE = auto(); FLOAT_TYPE = auto()
    BOOL_TYPE = auto(); BYTE_TYPE = auto(); VOID = auto()
    ANY = auto(); NEVER = auto()
    # Symbols
    DOT = auto(); COMMA = auto(); COLON = auto(); SEMICOLON = auto()
    LPAREN = auto(); RPAREN = auto()
    LBRACE = auto(); RBRACE = auto()
    LBRACKET = auto(); RBRACKET = auto()
    ARROW = auto(); FAT_ARROW = auto()
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto()
    PERCENT = auto(); CARET = auto(); TILDE = auto()
    AMP = auto(); PIPE = auto()
    EQ = auto(); NEQ = auto()
    LT = auto(); LTE = auto(); GT = auto(); GTE = auto()
    PLUS_EQ = auto(); MINUS_EQ = auto(); STAR_EQ = auto(); SLASH_EQ = auto()
    INC = auto(); DEC = auto()
    QUESTION = auto(); BANG = auto()
    # Special
    NEWLINE = auto(); INDENT = auto(); DEDENT = auto()
    EOF = auto()
    # Error
    ERROR = auto()

    # Re-alias for clarity
    AND = auto(); OR = auto(); NOT = auto()


# ── Keyword map ────────────────────────────────────────────────
KEYWORDS = {
    'module': TT.MODULE, 'import': TT.IMPORT, 'from': TT.FROM,
    'entity': TT.ENTITY, 'property': TT.PROPERTY, 'action': TT.ACTION,
    'proc': TT.PROC, 'flow': TT.FLOW, 'step': TT.STEP,
    'when': TT.WHEN, 'otherwise': TT.OTHERWISE, 'loop': TT.LOOP,
    'match': TT.MATCH, 'return': TT.RETURN, 'yield': TT.YIELD,
    'spawn': TT.SPAWN, 'await': TT.AWAIT, 'channel': TT.CHANNEL,
    'trait': TT.TRAIT, 'impl': TT.IMPLEMENT,
    'goal': TT.GOAL, 'constraint': TT.CONSTRAINT, 'guarantee': TT.GUARANTEE,
    'unsafe': TT.UNSAFE, 'owned': TT.OWNED, 'borrowed': TT.BORROWED,
    'let': TT.LET, 'var': TT.VAR,
    'Text': TT.TEXT, 'Int': TT.INT_TYPE, 'Float': TT.FLOAT_TYPE,
    'Bool': TT.BOOL_TYPE, 'Byte': TT.BYTE_TYPE, 'Void': TT.VOID,
    'Any': TT.ANY, 'Never': TT.NEVER,
    'true': TT.BOOL, 'false': TT.BOOL, 'none': TT.NONE,
    'and': TT.AND, 'or': TT.OR, 'not': TT.NOT,
    'property': TT.PROPERTY, 'intent': TT.IDENT, 'owner': TT.IDENT,
    'risk': TT.IDENT, 'depends': TT.IDENT, 'api': TT.IDENT,
    'testing': TT.IDENT, 'history': TT.IDENT, 'context': TT.IDENT,
}


@dataclass
class Token:
    type: TT
    value: str = ''
    line: int = 0
    col: int = 0

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.col})"


class LexerError(Exception):
    def __init__(self, msg, line, col):
        super().__init__(f"Lexer error at line {line}, col {col}: {msg}")
        self.line = line
        self.col = col


class Lexer:
    """Stateful lexer with indent tracking."""

    def __init__(self, source: str, filename: str = '<input>'):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.indent_stack: List[int] = [0]
        self.pending_dedents = 0

    def peek(self, offset=0) -> str:
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else '\0'

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace(self):
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r':
            self.advance()

    def skip_comment(self):
        if self.peek() == '#' and self.peek(1) == '#':
            # Block comment
            self.advance(); self.advance()
            while self.pos < len(self.source):
                if self.peek() == '#' and self.peek(1) == '#':
                    self.advance(); self.advance()
                    return
                self.advance()
        elif self.peek() == '#':
            # Line comment
            while self.pos < len(self.source) and self.peek() != '\n':
                self.advance()

    def read_string(self) -> Token:
        start_line, start_col = self.line, self.col
        quote = self.advance()  # consume opening quote
        parts = []
        while self.pos < len(self.source):
            ch = self.peek()
            if ch == quote:
                self.advance()
                return Token(TT.TEXT, ''.join(parts), start_line, start_col)
            if ch == '\\':
                self.advance()
                esc = self.advance()
                escape_map = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'"}
                parts.append(escape_map.get(esc, esc))
            else:
                parts.append(self.advance())
        raise LexerError("Unterminated string", start_line, start_col)

    def read_byte(self) -> Token:
        start_line, start_col = self.line, self.col
        self.advance()  # consume b
        self.advance()  # consume quote
        val = []
        while self.pos < len(self.source):
            ch = self.peek()
            if ch == '"':
                self.advance()
                return Token(TT.BYTE, bytes(''.join(val), 'utf-8').hex(), start_line, start_col)
            if ch == '\\':
                self.advance()
                esc = self.advance()
                val.append(esc)
            else:
                val.append(self.advance())
        raise LexerError("Unterminated byte literal", start_line, start_col)

    def read_number(self) -> Token:
        start_line, start_col = self.line, self.col
        num = ''
        is_float = False
        while self.pos < len(self.source) and (self.peek().isdigit() or self.peek() == '.'):
            if self.peek() == '.':
                if is_float:
                    break
                is_float = True
            num += self.advance()
        if is_float:
            return Token(TT.FLOAT, num, start_line, start_col)
        return Token(TT.INT, num, start_line, start_col)

    def read_ident(self) -> Token:
        start_line, start_col = self.line, self.col
        name = ''
        while self.pos < len(self.source) and (self.peek().isalnum() or self.peek() in '_-'):
            name += self.advance()
        tt = KEYWORDS.get(name, TT.IDENT)
        if tt == TT.BOOL:
            return Token(TT.BOOL, name, start_line, start_col)
        if tt == TT.NONE:
            return Token(TT.NONE, 'none', start_line, start_col)
        return Token(tt, name, start_line, start_col)

    def handle_indent(self):
        """Process indentation at start of line."""
        if self.pos >= len(self.source):
            return
        # Count spaces
        spaces = 0
        while self.pos < len(self.source) and self.source[self.pos] == ' ':
            spaces += 1
            self.advance()
        # Skip blank lines and comment-only lines
        if self.pos < len(self.source) and (self.peek() == '\n' or self.peek() == '#'):
            if self.peek() == '#':
                self.skip_comment()
            if self.peek() == '\n':
                self.advance()
                self.handle_indent()
                return
        current = self.indent_stack[-1]
        if spaces > current:
            self.indent_stack.append(spaces)
            self.tokens.append(Token(TT.INDENT, '', self.line, self.col))
        elif spaces < current:
            while self.indent_stack[-1] > spaces:
                self.indent_stack.pop()
                self.tokens.append(Token(TT.DEDENT, '', self.line, self.col))
            if self.indent_stack[-1] != spaces:
                raise LexerError(f"Indentation error: expected {self.indent_stack[-1]} spaces, got {spaces}", self.line, self.col)

    def tokenize(self) -> List[Token]:
        """Main tokenization loop."""
        while self.pos < len(self.source):
            self.skip_whitespace()

            if self.pos >= len(self.source):
                break

            ch = self.peek()

            # Newline
            if ch == '\n':
                self.advance()
                self.tokens.append(Token(TT.NEWLINE, '\\n', self.line, self.col))
                self.handle_indent()
                continue

            # Comment
            if ch == '#':
                self.skip_comment()
                continue

            # String
            if ch == '"' or ch == "'":
                self.tokens.append(self.read_string())
                continue

            # Byte literal
            if ch == 'b' and self.peek(1) == '"':
                self.tokens.append(self.read_byte())
                continue

            # Number
            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Identifier / keyword
            if ch.isalpha() or ch == '_':
                self.tokens.append(self.read_ident())
                continue

            # Two-char operators
            two = ch + (self.peek(1) if self.pos + 1 < len(self.source) else '')
            op_map = {
                '==': TT.EQ, '!=': TT.NEQ, '<=': TT.LTE, '>=': TT.GTE,
                '->': TT.ARROW, '=>': TT.FAT_ARROW, '+=': TT.PLUS_EQ,
                '-=': TT.MINUS_EQ, '*=': TT.STAR_EQ, '/=': TT.SLASH_EQ,
                '++': TT.INC, '--': TT.DEC, '<<': TT.AMP, '>>': TT.AMP,
            }
            if two in op_map:
                self.tokens.append(Token(op_map[two], two, self.line, self.col))
                self.advance(); self.advance()
                continue

            # Single-char operators
            single_map = {
                '.': TT.DOT, ',': TT.COMMA, ':': TT.COLON, ';': TT.SEMICOLON,
                '(': TT.LPAREN, ')': TT.RPAREN, '{': TT.LBRACE, '}': TT.RBRACE,
                '[': TT.LBRACKET, ']': TT.RBRACKET,
                '+': TT.PLUS, '-': TT.MINUS, '*': TT.STAR, '/': TT.SLASH,
                '%': TT.PERCENT, '^': TT.CARET, '~': TT.TILDE,
                '&': TT.AMP, '|': TT.PIPE,
                '<': TT.LT, '>': TT.GT,
                '=': TT.EQ, '?': TT.QUESTION, '!': TT.BANG,
            }
            if ch in single_map:
                self.tokens.append(Token(single_map[ch], ch, self.line, self.col))
                self.advance()
                continue

            raise LexerError(f"Unexpected character: {ch!r}", self.line, self.col)

        # Final dedents
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TT.DEDENT, '', self.line, self.col))

        self.tokens.append(Token(TT.EOF, '', self.line, self.col))
        return self.tokens


def tokenize(source: str, filename: str = '<input>') -> List[Token]:
    """Convenience function."""
    return Lexer(source, filename).tokenize()
