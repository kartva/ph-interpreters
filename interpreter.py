from ast_ import parse
import ast_

# Added EarlyReturn exception.
class EarlyReturn(Exception):
    def __init__(self, value):
        self.value = value

def interpret_expression(expression: ast_.Expression, ctx):
    pass

# --- Interpret an AST node. Returns the result, if any. May modify the given variables and functions dictionaries. ---
# We don't use default empty {} for variables and functions because https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
def interpret(astnode, \
              variables: dict[str, int], \
              functions: dict[str, ast_.FunctionDeclaration]):

    match astnode:
        # --- We're given a program. Execute the 'main' function ---
        case ast_.Program(function_declarations):
            # Interpret all functions to add them to the functions dictionary.
            for func in function_declarations:
                interpret(func, variables, functions)

            return interpret(ast_.CallExpression(ast_.Identifier("main"), []), variables, functions)

        # --- Handling a function declaration ---
        case ast_.FunctionDeclaration(name, args, body):
            functions[name] = ast_.FunctionDeclaration(name, args, body)

        # --- Handling simple statements ---

        case ast_.VarSetStatement(name, rhs):
            variables[name] = interpret(rhs, variables, functions)
        # Modified ReturnStatement to throw EarlyReturn.
        case ast_.ReturnStatement(expression):
            raise EarlyReturn(interpret(expression, variables, functions))
        case ast_.ExpressionStatement(expression):
            return interpret(expression, variables, functions)

        # --- Handling compound statements ---

        case ast_.BlockStatement(statements):
            for statement in statements:
                # Early return will propagate via exception; no special handling needed.
                interpret(statement, variables, functions)
        case ast_.IfStatement(condition, then_block, else_block):
            if interpret(condition, variables, functions):
                return interpret(then_block, variables, functions)
            elif else_block:
                return interpret(else_block, variables, functions)

        # TODO: Add WhileStatement case here

        # --- Handling expressions ---

        case ast_.NumberLiteral(value):
            return value
        case ast_.Identifier(_) as ident:
            return variables[ident]
        case ast_.BinaryExpression(left, operator, right):
            left_value = interpret(left, variables, functions)
            right_value = interpret(right, variables, functions)
            if operator == "+":
                return left_value + right_value
            elif operator == "-":
                return left_value - right_value
            elif operator == "*":
                return left_value * right_value
            elif operator == "/":
                return left_value / right_value
            elif operator == "<":
                return 1 if left_value < right_value else 0
            elif operator == ">":
                return 1 if left_value > right_value else 0
            elif operator == "==":
                return 1 if left_value == right_value else 0
            elif operator == "!=":
                return 1 if left_value != right_value else 0
            elif operator == "<=":
                return 1 if left_value <= right_value else 0
            elif operator == ">=":
                return 1 if left_value >= right_value else 0
            else:
                print(f"Unknown operator: {operator}")
                exit(1)

        case ast_.CallExpression(callee, arguments):
            if not isinstance(callee, ast_.Identifier):
                print(f"Invalid callee: {callee}")
                exit(1)
            callee: ast_.Identifier

            argument_values = [interpret(arg, variables, functions) for arg in arguments]

            # Intercept built-in functions
            if callee.ident == "print":
                print(argument_values[0])
                return

            fn_decl: ast_.FunctionDeclaration = functions[callee]

            child_scope = variables.copy()

            # zip(['a', 'b'], [1, 2]) -> [('a', 1), ('b', 2)]
            parameter_value_map = dict(zip(fn_decl.parameters, argument_values))
            child_scope.update(parameter_value_map)

            # Catch EarlyReturn when invoking the function body.
            try:
                result = interpret(fn_decl.body, child_scope, functions)
            except EarlyReturn as e:
                result = e.value
            return result

        case unknown:
            print(f"Unknown AST node: {unknown}")
            exit(1)

# --- Main program ---

import sys
def main():
    if len(sys.argv) != 2:
        print("Usage: python interpreter.py <file>")
        exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, 'r') as file:
            program_text = file.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        exit(1)

    program = parse(program_text)
    result = interpret(program, {}, {})
    print("main() returned: ", result)

if __name__ == "__main__":
    main()
