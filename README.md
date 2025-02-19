# Purdue Hackers Interpreters Workshop

This repository contains an implementation of the toy `klox` language written in Python (version 3.13 or above). File map:
- [`result.py`](result.py): a Result type implementation taken from [https://github.com/rustedpy/result](https://github.com/rustedpy/result)
- [`parser_combinator.py`](parser_combinator.py): a [parser combinator library](https://en.wikipedia.org/wiki/Parser_combinator)
- [`ast_.py`](ast_.py): contains AST node definitions and the language parser.
- [`interpreter.py`](interpreter.py): the whole point.

(TODO) Link to the workshop slideshow. Follow along!

## klox BNF grammer

Read the `*`, `+`, `[...]`, `?` symbols in the regex sense:
- `*`: zero or more of
- `+`: one or more of
- `[a-z]` one of the characters inside the square brackets. `a-z` means `a` to `z`.
- `?`: zero or one of (more intuitively, "optionally")

A rule is composed of the above and `|`s, which mean "or".

Example rule interpretations:
- `arg_list ::= expr (',' expr)*`: An `arg_list` is composed of an `expr`, followed by zero or more instances of a comma and another expression.
- `atom ::= ident
       | num
       | '(' atom ')'`: An `atom` is either an `ident`, a `num` or an opening brace `(` followed by another atom followed by the closing brace `)`.

```
ident ::= [a-zA-Z] [a-zA-Z0-9_]*
num ::= [0-9]+
atom ::= ident
       | num
       | '(' atom ')'

arg_list ::= expr (',' expr)*

call ::= ident '(' arg_list? ')'

unary ::= '-' unary
          | call
          | atom

product ::= unary '*' unary
          | unary '/' unary
          | unary

sum ::= product '+' product
      | product '-' product
      | product

expr ::= sum '>=' sum
       | sum '<=' sum
       | sum '<' sum
       | sum '>' sum
       | sum

var_set ::= ident '=' expr
var_decl ::= 'var' ident '=' expr
return ::= 'return' expr

if ::= 'if' '(' expr ')' stmt_block ( 'else' stmt_block )?
while ::= 'while' '(' expr ')' stmt_block

stmt ::= (return | if | while | var_decl | var_set | expr) ';'
stmt_block ::= '{' stmt+ '}'

param_list ::= ident (',' ident)*
fn ::= 'fn' ident '(' param_list? ')' stmt_block

program ::= fn+
```
