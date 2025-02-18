from typing import TypeVar, Generic, Tuple, Any, Union, Literal, Callable, TypeAlias, List
from parser_combinator import Parser, ParseSuccess, ParseError, ParseResult, Ok, Err

class ASTNode:
    pass

# --- A program is composed of function declarations ---

class Program(ASTNode):
    def __init__(self, funcs: List['FunctionDeclaration']):
        self.funcs = funcs
    def __repr__(self):
        return f"Program({self.funcs})"

class FunctionDeclaration(ASTNode):
    def __init__(self, name: 'Identifier', parameters: List['Identifier'], body: List['Statement']):
        self.name = name
        self.parameters = parameters
        self.body = body
    def __repr__(self):
        return f"fn {self.name} ({self.parameters}) {self.body})"

class Statement(ASTNode):
    pass

# --- Simple statements are statements that can't contain other statements ---

class VarSetStatement(Statement):
    def __init__(self, identifier: str, rhs: 'Expression'):
        self.name = identifier
        self.rhs = rhs
    def __repr__(self):
        return f"VarStatement({self.name}, {self.rhs})"
    
class ReturnStatement(Statement):
    def __init__(self, expression: 'Expression'):
        self.expression = expression
    def __repr__(self):
        return f"ReturnStatement({self.expression})"

# --- Compound statements are statements that can contain other statements ---

class IfStatement(Statement):
    def __init__(self, condition: 'Expression', then_block: List[Statement], else_block: List[Statement] | None):
        self.condition = condition
        self.then_block = then_block
        if else_block:
            self.else_block = else_block
        else:
            self.else_block = []
    def __repr__(self):
        return f"IfStatement({self.condition}, {self.then_block}, {self.else_block})"
    
class WhileStatement(Statement):
    def __init__(self, condition: 'Expression', block: List[Statement]):
        self.condition = condition
        self.block = block
    def __repr__(self):
        return f"WhileStatement({self.condition}, {self.block})"
    
class BlockStatement(Statement):
    def __init__(self, statements: List[Statement]):
        self.statements = statements
    def __repr__(self):
        return f"BlockStatement({self.statements})"

class ExpressionStatement(Statement):
    def __init__(self, expression: 'Expression'):
        self.expression = expression
    def __repr__(self):
        return f"{self.expression}"
    
# --- Expression classes start here ---

class Expression(ASTNode):
    pass

class BinaryExpression(Expression):
    def __init__(self, left: Expression, operator: str, right: Expression):
        self.left = left
        self.operator = operator
        self.right = right
    def __repr__(self):
        return f"({self.left} {self.operator} {self.right})"

class NumberLiteral(Expression):
    def __init__(self, value: int):
        self.value = value
    def __repr__(self):
        return f"{self.value}"
    
# TODO: replace instances of Identifier with NewType bind to str
class Identifier(Expression):
    def __init__(self, name: str):
        self.ident = name
    def __repr__(self):
        return f"{self.ident}"
    
class CallExpression(Expression):
    def __init__(self, callee: Expression, arguments: List[Expression]):
        self.callee = callee
        self.arguments = arguments
    def __repr__(self):
        return f"{self.callee}({', '.join(map(str, self.arguments))})"
    
def parse(s: str) -> Program:
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
        unary: Parser[Expression] = \
            p('-').repeated().map(lambda l: 1 if len(l) % 2 == 0 else -1) \
            .then(atom_or_call) \
            .map(lambda x: BinaryExpression(NumberLiteral(x[0]), '*', x[1]))
        
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

        return sum.or_else(product).or_else(unary)

    expr: Parser[Expression] = Parser.recursive(create_expr)

    var_set_stmt: Parser[Statement] = padded_ident.then_ignore(p('=')).then(expr).map(lambda t: VarSetStatement(t[0].ident, t[1]))
    return_stmt: Parser[Statement] = p('return').then(expr).map(ReturnStatement)

    def create_stmt_block(stmt_block: Parser[BlockStatement]) -> Parser[BlockStatement]:
        if_stmt = p("if").ignore_then(expr).then(stmt_block) \
            .then(p("else").ignore_then(stmt_block).or_not()) \
            .map(lambda t: IfStatement(t[0][0], t[0][1], t[1]))
        
        while_stmt = p("while").ignore_then(expr).then(stmt_block) \
            .map(lambda t: WhileStatement(t[0], t[1]))

        stmt: Parser[Statement] = return_stmt \
            .or_else(if_stmt) \
            .or_else(while_stmt) \
            .or_else(var_set_stmt) \
            .or_else(expr.map(ExpressionStatement))

        return stmt.then_ignore(p(';')).repeated().between(p('{'), p('}')).map(BlockStatement)

    stmt_block = Parser.recursive(create_stmt_block)
    fn_statement = p("fn") \
        .ignore_then(padded_ident) \
        .then(padded_ident.sep_by(p(',')).between(p('('), p(')'))) \
        .then(stmt_block).map(lambda t: FunctionDeclaration(t[0][0], t[0][1], t[1]))

    program_parser: Parser[Program] = fn_statement.repeated().map(Program)

    parsed, _ = (program_parser.eof())(s).unwrap()
    return parsed

def main():
    program = parse("""
                    fn add(a, b) { return a + b; }""")
    print(program)

if __name__ == "__main__":
    main()