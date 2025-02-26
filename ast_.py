from typing import TypeVar, Generic, Tuple, Any, Union, Literal, Callable, TypeAlias, List
from parser_combinator import Parser, ParseSuccess, ParseError, ParseResult, Ok, Err

class ASTNode:
    __match_args__ = ()  # No attributes for base ASTNode

# --- A program is composed of function declarations ---

class Program(ASTNode):
    __match_args__ = ("funcs",)
    def __init__(self, funcs: List['FunctionDeclaration']):
        self.funcs = funcs
    def __repr__(self):
        return f"Program({self.funcs})"

class FunctionDeclaration(ASTNode):
    __match_args__ = ("name", "parameters", "body")
    def __init__(self, name: 'Identifier', parameters: List['Identifier'], body: 'BlockStatement'):
        self.name = name
        self.parameters = parameters
        self.body = body
    def __repr__(self):
        return f"fn {self.name} ({self.parameters}) {self.body})"

# --- A function contains a list of statements ---

class Statement(ASTNode):
    pass

# --- Simple statements are statements that can't contain other statements ---

class VarSetStatement(Statement):
    __match_args__ = ("name", "rhs")
    def __init__(self, identifier: str, rhs: 'Expression'):
        self.name = identifier
        self.rhs = rhs
    def __repr__(self):
        return f"VarStatement({self.name}, {self.rhs})"

class ReturnStatement(Statement):
    __match_args__ = ("expression",)
    def __init__(self, expression: 'Expression'):
        self.expression = expression
    def __repr__(self):
        return f"ReturnStatement({self.expression})"

# '2;' is an example of an expression statement.
class ExpressionStatement(Statement):
    __match_args__ = ("expression",)
    def __init__(self, expression: 'Expression'):
        self.expression = expression
    def __repr__(self):
        return f"{self.expression}"

# --- Compound statements are statements that can contain other statements ---

class BlockStatement(Statement):
    __match_args__ = ("statements",)
    def __init__(self, statements: List[Statement]):
        self.statements = statements
    def __repr__(self):
        return f"BlockStatement({self.statements})"

class IfStatement(Statement):
    __match_args__ = ("condition", "then_block", "else_block")
    def __init__(self, condition: 'Expression', then_block: BlockStatement, else_block: BlockStatement | None):
        self.condition = condition
        self.then_block = then_block
        if else_block:
            self.else_block = else_block
        else:
            self.else_block = []
    def __repr__(self):
        return f"IfStatement({self.condition}, {self.then_block}, {self.else_block})"

class WhileStatement(Statement):
    __match_args__ = ("condition", "block")
    def __init__(self, condition: 'Expression', block: BlockStatement):
        self.condition = condition
        self.block = block
    def __repr__(self):
        return f"WhileStatement({self.condition}, {self.block})"

# --- Statements may contain expressions. ---

class Expression(ASTNode):
    __match_args__ = ()  # Base Expression has no fields

class NumberLiteral(Expression):
    __match_args__ = ("value",)
    def __init__(self, value: int):
        self.value = value
    def __repr__(self):
        return f"{self.value}"

# TODO: replace instances of Identifier with NewType bind to str

class Identifier(Expression):
    __match_args__ = ("ident",)
    def __init__(self, name: str):
        self.ident = name
    def __repr__(self):
        return f"{self.ident}"
    def __eq__(self, value):
        return isinstance(value, Identifier) and self.ident == value.ident
    def __hash__(self):
        return hash(self.ident)

class BinaryExpression(Expression):
    __match_args__ = ("left", "operator", "right")
    def __init__(self, left: Expression, operator: str, right: Expression):
        self.left = left
        self.operator = operator
        self.right = right
    def __repr__(self):
        return f"({self.left} {self.operator} {self.right})"


class CallExpression(Expression):
    __match_args__ = ("callee", "arguments")
    def __init__(self, callee: Expression, arguments: List[Expression]):
        self.callee = callee
        self.arguments = arguments
    def __repr__(self):
        return f"{self.callee}({', '.join(map(str, self.arguments))})"

def parse(s: str, debug=False) -> Program:
    if debug: Parser.enable_debug()

    p = lambda x: Parser.just(x).padded()
    padded_ident = Parser.ident().padded().map(Identifier)

    def create_expr(expr: Parser[Expression]) -> Parser[Expression]:
        num: Parser[NumberLiteral] = Parser.number().padded().map(NumberLiteral)

        # An atom is either a number, a variable reference, or an expression in parentheses.
        atom: Parser[Expression] = num \
            .or_else(padded_ident) \
            .or_else(expr.between(p('('), p(')')))

        call: Parser[Expression] = atom \
            .then_ignore(p('(')) \
            .then(expr.sep_by(p(','))) \
            .then_ignore(p(')')) \
            .map(lambda t: CallExpression(t[0], t[1]))

        atom_or_call = call.or_else(atom)

        # note that unary is defined in terms of atom, NOT expr
        # this is important to prevent parsing -2 * 2 as -(2 * 2)

        # rewrite -10 as -1 * 10
        unary: Parser[Expression] = \
            p('-').repeated().map(lambda l: 1 if len(l) % 2 == 0 else -1) \
            .then(atom_or_call) \
            .map(lambda x: BinaryExpression(NumberLiteral(x[0]), '*', x[1]) if x[0] == -1 else x[1])

        def foldl(t: Tuple[Expression, List[Tuple[str, Expression]]]) -> Expression:
            left, right = t
            for op, expr in right:
                left = BinaryExpression(left, op, expr)
            return left

        product: Parser[Expression] = unary \
            .then(
                (p('*').or_else(p('/'))).then(unary).repeated()
            ).map(foldl)

        sum: Parser[Expression] = product \
            .then(
                (p('+').or_else(p('-'))).then(product).repeated()
            ).map(foldl)

        compare: Parser[Expression] = sum \
            .then(
                (p('==').or_else(p('!=')).or_else(p('<').or_else(p('>'))).or_else(p('<=').or_else(p('>='))).then(sum)).repeated()
            ).map(foldl)

        return compare.or_else(sum).or_else(product).or_else(unary)

    expr: Parser[Expression] = Parser.recursive(create_expr)

    var_set_stmt: Parser[Statement] = padded_ident.then_ignore(p('=')).then(expr).map(lambda t: VarSetStatement(t[0].ident, t[1]))
    return_stmt: Parser[Statement] = p('return').ignore_then(expr).map(ReturnStatement)

    def create_stmt_block(stmt_block: Parser[BlockStatement]) -> Parser[BlockStatement]:
        if_stmt = p("if").ignore_then(expr).then(stmt_block) \
            .then(p("else").ignore_then(stmt_block).or_not()) \
            .map(lambda t: \
                IfStatement(t[0][0], t[0][1], t[1]))

        while_stmt = None # TODO: add parser combinator expression for while statement

        stmt: Parser[Statement] = return_stmt \
            .or_else(if_stmt) \
            .or_else(while_stmt) \
            .or_else(var_set_stmt) \
            .or_else(expr.map(ExpressionStatement))

        return stmt.then_ignore(p(';')).repeated().between(p('{'), p('}')).map(BlockStatement)

    stmt_block: Parser[BlockStatement] = Parser.recursive(create_stmt_block)
    fn_statement = p("fn") \
        .ignore_then(padded_ident) \
        .then(padded_ident.sep_by(p(',')).between(p('('), p(')'))) \
        .then(stmt_block).map(lambda t: FunctionDeclaration(t[0][0], t[0][1], t[1]))

    program_parser: Parser[Program] = fn_statement.repeated().map(Program)

    parsed, _ = (program_parser.eof())(s).unwrap()
    return parsed
