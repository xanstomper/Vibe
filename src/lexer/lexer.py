"""
Vibe Language Lexer

Tokenizes Vibe source code into a stream of tokens
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class TokenType(Enum):
    """Token types"""
    # Literals
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"
    CHAR = "CHAR"
    BOOL = "BOOL"
    
    # Identifiers and keywords
    IDENTIFIER = "IDENTIFIER"
    MODULE = "MODULE"
    IMPORT = "IMPORT"
    FROM = "FROM"
    AS = "AS"
    LET = "LET"
    MUT = "MUT"
    CONST = "CONST"
    FUNC = "FUNC"
    PROC = "PROC"
    STRUCT = "STRUCT"
    ENUM = "ENUM"
    TRAIT = "TRAIT"
    TYPE = "TYPE"
    RETURN = "RETURN"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    FOR = "FOR"
    IN = "IN"
    MATCH = "MATCH"
    SPAWN = "SPAWN"
    AWAIT = "AWAIT"
    NONE = "NONE"
    OK = "OK"
    ERROR = "ERROR"
    UNSAFE = "UNSAFE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    TRUE = "TRUE"
    FALSE = "FALSE"
    SELF = "SELF"
    
    # Metadata keywords
    INTENT = "INTENT"
    OWNER = "OWNER"
    RISK = "RISK"
    DEPENDENCIES = "DEPENDENCIES"
    API_SURFACE = "API_SURFACE"
    TESTING = "TESTING"
    UNIT = "UNIT"
    INTEGRATION = "INTEGRATION"
    COVERAGE = "COVERAGE"
    THRESHOLD = "THRESHOLD"
    
    # Operators
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    PERCENT = "PERCENT"
    POWER = "POWER"
    
    EQ = "EQ"
    NEQ = "NEQ"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    
    AND_AND = "AND_AND"
    OR_OR = "OR_OR"
    
    BIT_AND = "BIT_AND"
    BIT_OR = "BIT_OR"
    BIT_XOR = "BIT_XOR"
    BIT_NOT = "BIT_NOT"
    SHL = "SHL"
    SHR = "SHR"
    
    ASSIGN = "ASSIGN"
    PLUS_ASSIGN = "PLUS_ASSIGN"
    MINUS_ASSIGN = "MINUS_ASSIGN"
    STAR_ASSIGN = "STAR_ASSIGN"
    SLASH_ASSIGN = "SLASH_ASSIGN"
    PERCENT_ASSIGN = "PERCENT_ASSIGN"
    
    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"
    
    # Delimiters
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    LANGLE = "LANGLE"
    RANGLE = "RANGLE"
    COLON = "COLON"
    DOUBLE_COLON = "DOUBLE_COLON"
    SEMICOLON = "SEMICOLON"
    COMMA = "COMMA"
    DOT = "DOT"
    ARROW = "ARROW"
    THICK_ARROW = "THICK_ARROW"
    QUESTION = "QUESTION"
    EXCLAMATION = "EXCLAMATION"
    DOLLAR = "DOLLAR"
    HASH = "HASH"
    DOUBLE_HASH = "DOUBLE_HASH"
    AT = "AT"
    UNDERSCORE = "UNDERSCORE"
    
    # Special
    NEWLINE = "NEWLINE"
    INDENT = "INDENT"
    DEDENT = "DEDENT"
    EOF = "EOF"
    ERROR_TOKEN = "ERROR_TOKEN"


@dataclass
class Token:
    """A single token"""
    type: TokenType
    value: str
    line: int
    column: int
    length: int = 1
    
    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', line={self.line}, col={self.column})"


class LexerError(Exception):
    """Lexer error"""
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}, Column {column}: {message}")


class Lexer:
    """Vibe language lexer"""
    
    # Keywords mapping
    KEYWORDS = {
        'module': TokenType.MODULE,
        'import': TokenType.IMPORT,
        'from': TokenType.FROM,
        'as': TokenType.AS,
        'let': TokenType.LET,
        'mut': TokenType.MUT,
        'const': TokenType.CONST,
        'func': TokenType.FUNC,
        'proc': TokenType.PROC,
        'struct': TokenType.STRUCT,
        'enum': TokenType.ENUM,
        'trait': TokenType.TRAIT,
        'type': TokenType.TYPE,
        'return': TokenType.RETURN,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'while': TokenType.WHILE,
        'for': TokenType.FOR,
        'in': TokenType.IN,
        'match': TokenType.MATCH,
        'spawn': TokenType.SPAWN,
        'await': TokenType.AWAIT,
        'none': TokenType.NONE,
        'ok': TokenType.OK,
        'error': TokenType.ERROR,
        'unsafe': TokenType.UNSAFE,
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        'self': TokenType.SELF,
        'intent': TokenType.INTENT,
        'owner': TokenType.OWNER,
        'risk': TokenType.RISK,
        'dependencies': TokenType.DEPENDENCIES,
        'api_surface': TokenType.API_SURFACE,
        'testing': TokenType.TESTING,
        'unit': TokenType.UNIT,
        'integration': TokenType.INTEGRATION,
        'coverage': TokenType.COVERAGE,
        'threshold': TokenType.THRESHOLD,
    }
    
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.indent_stack: List[int] = [0]
        self.pending_tokens: List[Token] = []
    
    def error(self, message: str) -> LexerError:
        """Create a lexer error"""
        return LexerError(message, self.line, self.column)
    
    def peek(self) -> Optional[str]:
        """Peek at current character"""
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None
    
    def peek_next(self) -> Optional[str]:
        """Peek at next character"""
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return None
    
    def advance(self) -> str:
        """Advance to next character"""
        if self.pos >= len(self.source):
            raise self.error("Unexpected end of file")
        
        ch = self.source[self.pos]
        self.pos += 1
        
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        
        return ch
    
    def skip_whitespace(self):
        """Skip whitespace (not newlines)"""
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r':
            self.advance()
    
    def skip_comment(self):
        """Skip single-line comment"""
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            self.advance()
    
    def skip_block_comment(self):
        """Skip multi-line comment"""
        depth = 1
        while self.pos < len(self.source) and depth > 0:
            if self.source[self.pos] == '#' and self.peek_next() == '#':
                depth += 1
                self.advance()
                self.advance()
            elif self.source[self.pos] == '#' and self.peek_next() == '#':
                # Check for single # at end
                pass
            elif self.source[self.pos] == '#':
                # End of block comment
                depth -= 1
                self.advance()
            else:
                self.advance()
        
        if depth > 0:
            raise self.error("Unterminated block comment")
    
    def read_string(self) -> Token:
        """Read string literal"""
        start_line, start_col = self.line, self.column
        self.advance()  # Skip opening quote
        
        value = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            
            if ch == '"':
                self.advance()  # Skip closing quote
                return Token(TokenType.STRING, ''.join(value), start_line, start_col)
            
            if ch == '\\':
                self.advance()
                escape_ch = self.advance()
                
                escape_map = {
                    'n': '\n',
                    't': '\t',
                    'r': '\r',
                    '\\': '\\',
                    '"': '"',
                    '0': '\0',
                }
                value.append(escape_map.get(escape_ch, escape_ch))
            else:
                value.append(self.advance())
        
        raise self.error("Unterminated string")
    
    def read_char(self) -> Token:
        """Read character literal"""
        start_line, start_col = self.line, self.column
        self.advance()  # Skip opening quote
        
        if self.peek() == '\\':
            self.advance()
            ch = self.advance()
            escape_map = {
                'n': '\n',
                't': '\t',
                'r': '\r',
                '\\': '\\',
                "'": "'",
                '0': '\0',
            }
            value = escape_map.get(ch, ch)
        else:
            value = self.advance()
        
        if self.peek() != "'":
            raise self.error("Unterminated character literal")
        self.advance()  # Skip closing quote
        
        return Token(TokenType.CHAR, value, start_line, start_col)
    
    def read_number(self) -> Token:
        """Read number literal"""
        start_line, start_col = self.line, self.column
        value = []
        is_float = False
        
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            
            if ch.isdigit():
                value.append(self.advance())
            elif ch == '.' and not is_float:
                is_float = True
                value.append(self.advance())
            else:
                break
        
        if is_float:
            return Token(TokenType.FLOAT, ''.join(value), start_line, start_col)
        else:
            return Token(TokenType.INT, ''.join(value), start_line, start_col)
    
    def read_identifier(self) -> Token:
        """Read identifier or keyword"""
        start_line, start_col = self.line, self.column
        value = []
        
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch.isalnum() or ch == '_':
                value.append(self.advance())
            else:
                break
        
        word = ''.join(value)
        token_type = self.KEYWORDS.get(word, TokenType.IDENTIFIER)
        
        return Token(token_type, word, start_line, start_col)
    
    def add_token(self, token_type: TokenType, value: str, 
                  start_line: int, start_col: int, length: int = 1):
        """Add a token"""
        self.tokens.append(Token(token_type, value, start_line, start_col, length))
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire source"""
        while self.pos < len(self.source):
            self.skip_whitespace()
            
            if self.pos >= len(self.source):
                break
            
            start_line, start_col = self.line, self.column
            ch = self.source[self.pos]
            
            # Newlines
            if ch == '\n':
                self.advance()
                self.add_token(TokenType.NEWLINE, '\n', start_line, start_col)
            
            # Comments
            elif ch == '#':
                self.advance()
                if self.peek() == '#':
                    # Block comment
                    self.advance()
                    self.skip_block_comment()
                else:
                    # Single-line comment
                    self.skip_comment()
            
            # Strings
            elif ch == '"':
                token = self.read_string()
                self.tokens.append(token)
            
            # Characters
            elif ch == "'":
                token = self.read_char()
                self.tokens.append(token)
            
            # Numbers
            elif ch.isdigit():
                token = self.read_number()
                self.tokens.append(token)
            
            # Identifiers and keywords
            elif ch.isalpha() or ch == '_':
                token = self.read_identifier()
                self.tokens.append(token)
            
            # Operators and delimiters
            elif ch == '+':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.PLUS_ASSIGN, '+=', start_line, start_col, 2)
                elif self.peek() == '+':
                    self.advance()
                    self.add_token(TokenType.INCREMENT, '++', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.PLUS, '+', start_line, start_col)
            
            elif ch == '-':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.MINUS_ASSIGN, '-=', start_line, start_col, 2)
                elif self.peek() == '-':
                    self.advance()
                    self.add_token(TokenType.DECREMENT, '--', start_line, start_col, 2)
                elif self.peek() == '>':
                    self.advance()
                    self.add_token(TokenType.ARROW, '->', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.MINUS, '-', start_line, start_col)
            
            elif ch == '*':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.STAR_ASSIGN, '*=', start_line, start_col, 2)
                elif self.peek() == '*':
                    self.advance()
                    self.add_token(TokenType.POWER, '**', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.STAR, '*', start_line, start_col)
            
            elif ch == '/':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.SLASH_ASSIGN, '/=', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.SLASH, '/', start_line, start_col)
            
            elif ch == '%':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.PERCENT_ASSIGN, '%=', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.PERCENT, '%', start_line, start_col)
            
            elif ch == '=':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.EQ, '==', start_line, start_col, 2)
                elif self.peek() == '>':
                    self.advance()
                    self.add_token(TokenType.THICK_ARROW, '=>', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.ASSIGN, '=', start_line, start_col)
            
            elif ch == '!':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.NEQ, '!=', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.EXCLAMATION, '!', start_line, start_col)
            
            elif ch == '<':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.LTE, '<=', start_line, start_col, 2)
                elif self.peek() == '<':
                    self.advance()
                    self.add_token(TokenType.SHL, '<<', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.LANGLE, '<', start_line, start_col)
            
            elif ch == '>':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.add_token(TokenType.GTE, '>=', start_line, start_col, 2)
                elif self.peek() == '>':
                    self.advance()
                    self.add_token(TokenType.SHR, '>>', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.GT, '>', start_line, start_col)
            
            elif ch == '&':
                self.advance()
                if self.peek() == '&':
                    self.advance()
                    self.add_token(TokenType.AND_AND, '&&', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.BIT_AND, '&', start_line, start_col)
            
            elif ch == '|':
                self.advance()
                if self.peek() == '|':
                    self.advance()
                    self.add_token(TokenType.OR_OR, '||', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.BIT_OR, '|', start_line, start_col)
            
            elif ch == '^':
                self.advance()
                self.add_token(TokenType.BIT_XOR, '^', start_line, start_col)
            
            elif ch == '~':
                self.advance()
                self.add_token(TokenType.BIT_NOT, '~', start_line, start_col)
            
            elif ch == '(':
                self.advance()
                self.add_token(TokenType.LPAREN, '(', start_line, start_col)
            
            elif ch == ')':
                self.advance()
                self.add_token(TokenType.RPAREN, ')', start_line, start_col)
            
            elif ch == '{':
                self.advance()
                self.add_token(TokenType.LBRACE, '{', start_line, start_col)
            
            elif ch == '}':
                self.advance()
                self.add_token(TokenType.RBRACE, '}', start_line, start_col)
            
            elif ch == '[':
                self.advance()
                self.add_token(TokenType.LBRACKET, '[', start_line, start_col)
            
            elif ch == ']':
                self.advance()
                self.add_token(TokenType.RBRACKET, ']', start_line, start_col)
            
            elif ch == ':':
                self.advance()
                if self.peek() == ':':
                    self.advance()
                    self.add_token(TokenType.DOUBLE_COLON, '::', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.COLON, ':', start_line, start_col)
            
            elif ch == ';':
                self.advance()
                self.add_token(TokenType.SEMICOLON, ';', start_line, start_col)
            
            elif ch == ',':
                self.advance()
                self.add_token(TokenType.COMMA, ',', start_line, start_col)
            
            elif ch == '.':
                self.advance()
                self.add_token(TokenType.DOT, '.', start_line, start_col)
            
            elif ch == '?':
                self.advance()
                self.add_token(TokenType.QUESTION, '?', start_line, start_col)
            
            elif ch == '@':
                self.advance()
                self.add_token(TokenType.AT, '@', start_line, start_col)
            
            elif ch == '$':
                self.advance()
                self.add_token(TokenType.DOLLAR, '$', start_line, start_col)
            
            elif ch == '#':
                self.advance()
                if self.peek() == '#':
                    self.advance()
                    self.add_token(TokenType.DOUBLE_HASH, '##', start_line, start_col, 2)
                else:
                    self.add_token(TokenType.HASH, '#', start_line, start_col)
            
            else:
                raise self.error(f"Unexpected character: {ch}")
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens


def tokenize(source: str, filename: str = "<stdin>") -> List[Token]:
    """Convenience function to tokenize source"""
    lexer = Lexer(source, filename)
    return lexer.tokenize()
