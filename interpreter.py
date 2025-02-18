from parse_ast import parse
import parse_ast

def interpret_expression(expression: parse_ast.Expression, ctx):
    pass

def interpret(program: parse_ast.Program):
    statements = program.funcs

    variables = {}
    for statement in statements:
        match statement:
            case parse_ast.LetStatement(name, value):
                variables[name] = interpret(value)
            case unknown:
                print(f"Unknown statement: {unknown}")
                exit(1)

def main():
    program = parse("let x = 5; let y = -10 / 2 * 3 + fn(1, 2 + 3); print(x)")
    print(program)

if __name__ == "__main__":
    main()