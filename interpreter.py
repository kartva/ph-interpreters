from parse_ast import parse
import parse_ast

def interpret_expression(expression: parse_ast.Expression, ctx):
    pass

# --- Interpret an AST node. Returns the result, if any. May modify the given variables and functions dictionaries. ---
# We don't use default empty {} for variables and functions because https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
def interpret(astnode, \
              variables: dict[str, int] | None = None, \
              functions: dict[str, parse_ast.FunctionDeclaration] | None = None):

    if variables is None:
        variables = {}
    if functions is None:
        functions = {}

    match astnode:
        # --- We're given a program. Execute the 'main' function ---
        case parse_ast.Program(function_declarations):
            # Interpret all functions to add them to the functions dictionary.
            for func in function_declarations:
                interpret(func, variables, functions)
            
            print(functions)
            main_fn = functions["main"]
            return interpret(main_fn, variables, functions)

        # --- Handling a function declaration ---
        case parse_ast.FunctionDeclaration(name, args, body):
            functions[name] = parse_ast.FunctionDeclaration(name, args, body)

        # --- Handling simple statements ---

        case parse_ast.VarSetStatement(name, rhs):
            variables[name] = interpret(rhs)
        case parse_ast.ReturnStatement(expression):
            # We handle propagating the return value from the function in the CallExpression case.
            return interpret(expression, variables, functions)
        case parse_ast.ExpressionStatement(expression):
            return interpret(expression, variables, functions)
        
        # --- Handling compound statements ---

        case parse_ast.BlockStatement(statements):
            # Create a new scope so that variables declared in this block don't leak out.
            child_scope = variables.copy()
            for statement in statements:
                if isinstance(statement, parse_ast.ReturnStatement):
                    return interpret(statement, child_scope, functions)
                interpret(statement, child_scope, functions)
        case parse_ast.IfStatement(condition, then_block, else_block):
            if interpret(condition, variables, functions):
                return interpret(then_block, variables, functions)
            elif else_block:
                return interpret(else_block, variables, functions)
        case parse_ast.WhileStatement(condition, body):
            while interpret(condition, variables, functions):
                interpret(body, variables, functions)

        # --- Handling expressions ---

        case parse_ast.NumberLiteral(value):
            return value
        case parse_ast.Identifier(name):
            return variables[name]
        case parse_ast.BinaryExpression(left, operator, right):
            left_value = interpret(left, variables)
            right_value = interpret(right, variables)
            if operator == "+":
                return left_value + right_value
            elif operator == "-":
                return left_value - right_value
            elif operator == "*":
                return left_value * right_value
            elif operator == "/":
                return left_value / right_value
            else:
                print(f"Unknown operator: {operator}")
                exit(1)

        case parse_ast.CallExpression(callee, arguments):
            if not isinstance(callee, parse_ast.Identifier):
                print(f"Invalid callee: {callee}")
                exit(1)
            callee: parse_ast.Identifier

            argument_values = [interpret(arg, variables, functions) for arg in arguments]

            # Intercept built-in functions
            if callee.ident == "print":
                print(argument_values[0])
                return

            fn_decl: parse_ast.FunctionDeclaration = functions[callee.ident]

            child_scope = variables.copy()

            # zip(['a', 'b'], [1, 2]) -> [('a', 1), ('b', 2)]
            arg_value_map = dict(zip(fn_decl.args, argument_values))
            child_scope.update(arg_value_map)

            return interpret(fn_decl.body, child_scope, functions)

        case unknown:
            print(f"Unknown AST node: {unknown}")
            exit(1)

def main():
    program = parse("""
                    fn factorial(n) {
                        if n {
                            return n * factorial(n - 1);
                        } else {
                            return 1;
                        };
                    }
                    fn main() {
                        print(factorial(5));
                        return 0;
                    }""")
    print(program)
    result = interpret(program)
    print(result)

if __name__ == "__main__":
    main()