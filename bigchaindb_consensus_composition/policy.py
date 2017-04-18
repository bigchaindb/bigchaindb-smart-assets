import re
import os

import ply.lex as lex
import ply.yacc as yacc


class PolicyParser():
    reserved = {
        'AND': 'AND',
        'OR': 'OR',
        'LEN': 'LEN',
        'SUM': 'SUM',
        'AMOUNT': 'AMOUNT'
    }

    # List of token names.   This is always required
    tokens = (
        'NUMBER',
        'COMMA',
        'PLUS',
        'MINUS',
        'TIMES',
        'DIVIDE',
        'LPAREN',
        'RPAREN',
        'LBRACK',
        'RBRACK',
        'EQ',
        'LT',
        'LEQ',
        'GT',
        'GEQ',
        'ID',
        'TX',
        'STRING'
     ) + tuple(reserved.values())

    # Regular expression rules for simple tokens
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_LBRACK = r'\['
    t_RBRACK = r'\]'
    t_EQ = r'=='
    t_LT = r'<'
    t_GT = r'>'
    t_LEQ = r'<='
    t_GEQ = r'>='
    t_COMMA = r','

    precedence = (
        ('nonassoc', 'EQ', 'LT', 'GT', 'LEQ', 'GEQ'),  # Nonassociative operators
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE'),
        ('right', 'UMINUS'),
    )

    # Build the lexer
    def __init__(self, transaction=None, **kwargs):
        self.debug = kwargs.get('debug', 0)
        self.names = {}
        try:
            modname = os.path.split(os.path.splitext(__file__)[0])[1] + "_" + self.__class__.__name__
        except:
            modname = "parser" + "_" + self.__class__.__name__
        self.debugfile = modname + ".dbg"
        self.tabmodule = modname + "_" + "parsetab"

        self.transaction = transaction
        self.lexer = lex.lex(module=self, **kwargs)
        self.parser = yacc.yacc(module=self,
                                debug=self.debug,
                                debugfile=self.debugfile,
                                tabmodule=self.tabmodule)

    def input(self, *args, **kwargs):
        return self.lexer.input(*args, **kwargs)

    def token(self, *args, **kwargs):
        return self.lexer.token(*args, **kwargs)

    def parse(self, *args, **kwargs):
        return self.parser.parse(*args, **kwargs)

    def t_TX(self, t):
        r'transaction.[a-zA-Z_0-9\'\"\[\]\.]*'
        try:
            # TODO: improve eval (should be somewhat safeguarded)
            value = eval('self.' + t.value)
            t.type = self.reserved.get(t.value, 'TX')  # Check for reserved words
            t.value = value
        except (AttributeError, KeyError):
            # TODO: improve
            t.lexer.skip(1)
        return t

    # A regular expression rule with some action code
    def t_NUMBER(self, t):
        r'[\"\']*\d+[\"\']*'
        if isinstance(t.value, str):
            t.value = re.sub('[\'\"]', '', t.value)
        t.value = int(t.value)
        return t

    def t_STRING(self, t):
        r'[\"\']+[a-zA-Z_0-9]*[\"\']+'
        t.type = self.reserved.get(t.value, 'STRING')  # Check for reserved words
        t.value = str(t.value[1:-1])
        return t

    def t_ID(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9]*'
        t.type = self.reserved.get(t.value, 'ID')  # Check for reserved words
        return t

    # Define a rule so we can track line numbers
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # A string containing ignored characters (spaces and tabs)
    t_ignore = ' \t'

    # Error handling rule
    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def p_binary_operators(self, p):
        """expression : expression PLUS term
                      | expression MINUS term
           term       : term TIMES factor
                      | term DIVIDE factor"""
        if p[2] == '+':
            p[0] = p[1] + p[3]
        elif p[2] == '-':
            p[0] = p[1] - p[3]
        elif p[2] == '*':
            p[0] = p[1] * p[3]
        elif p[2] == '/':
            p[0] = p[1] / p[3]

    def p_comparison(self, p):
        """expression : expression EQ expression
                      | expression GT expression
                      | expression LT expression
                      | expression GEQ expression
                      | expression LEQ expression"""
        if p[2] == '==':
            p[0] = p[1] == p[3]
        elif p[2] == '<':
            p[0] = p[1] < p[3]
        elif p[2] == '>':
            p[0] = p[1] > p[3]
        elif p[2] == '>=':
            p[0] = p[1] >= p[3]
        elif p[2] == '<=':
            p[0] = p[1] <= p[3]

    def p_boolean(self, p):
        """expression : expression AND expression
                      | expression OR expression"""
        if p[2] == 'AND':
            p[0] = p[1] and p[3]
        elif p[2] == 'OR':
            p[0] = p[1] or p[3]

    def p_expression_uminus(self, p):
        """expression : MINUS expression %prec UMINUS"""
        p[0] = -p[2]

    def p_expression_term(self, p):
        """expression : term"""
        p[0] = p[1]

    def p_expression_aggregate(self, p):
        """expression : func LPAREN list RPAREN"""
        if p[1] == 'LEN':
            p[0] = len(p[3])
        elif p[1] == 'SUM':
            p[0] = sum(p[3])
        elif p[1] == 'AMOUNT':
            # TODO prechecks
            p[0] = sum([output.amount for output in p[3]])

    def p_list_term(self, p):
        """list : term
                | list COMMA term"""
        if len(p) == 2:
            if isinstance(p[1], list):
                p[0] = p[1]
            else:
                p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[3]]

    def p_list(self, p):
        """list : LBRACK list RBRACK"""
        p[0] = p[2]

    def p_term_factor(self, p):
        """term : factor"""
        p[0] = p[1]

    def p_functions(self, p):
        """func : LEN
                | SUM
                | AMOUNT"""
        p[0] = p[1]

    def p_factor(self, p):
        """factor : NUMBER
                  | STRING
                  | ID
                  | TX"""
        p[0] = p[1]

    def p_factor_expr(self, p):
        """factor : LPAREN expression RPAREN"""
        p[0] = p[2]

    # Error rule for syntax errors
    def p_error(self, p):
        print("Syntax error in input!")
