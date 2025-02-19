from result import Ok, Err, Result
from typing import TypeVar, Generic, Tuple, Any, Union, Literal, Callable, TypeAlias, List

type ParseSuccess[T] = Tuple[T, str]
type ParseError = str
type ParseResult[T] = Result[ParseSuccess[T], ParseError]

class Parser[T]:
    """A parser is an object that can be called with a string. It returns either a ParseSuccess or a ParseError.
    ParseSuccess is a tuple of the parsed value and the rest of the input, while the ParseError is an error message consisting of a string."""

    _debug_enabled = False
    _debug_indent = 0

    def __init__(self, parse: Callable[[str], Result[ParseSuccess[T], ParseError]], name: str = None):
        self.parse = parse
        self.name = name or "anonymous"

    def __call__(self, input: str) -> Result[ParseSuccess[T], ParseError]:
        if Parser._debug_enabled:
            print(f"{'  ' * Parser._debug_indent}Trying {self.name} on: {input[:20]}...")
            Parser._debug_indent += 1
            
        result = self.parse(input)
        
        if Parser._debug_enabled:
            Parser._debug_indent -= 1
            status = "succeeded" if result.is_ok() else "failed"
            print(f"{'  ' * Parser._debug_indent}{self.name} {status}: {result}")
            
        return result

    @staticmethod
    def enable_debug():
        """Enable debug mode for all parsers"""
        Parser._debug_enabled = True
        Parser._debug_indent = 0

    @staticmethod
    def disable_debug():
        """Disable debug mode for all parsers"""
        Parser._debug_enabled = False
        Parser._debug_indent = 0

    def label(self, name: str) -> 'Parser[T]':
        """Give this parser a name for debug output"""
        self.name = name
        return self

    def map[U](self, f: Callable[[T], U]) -> 'Parser[U]':
        """Apply a function to the result of the parser."""
        def new_parser(input: str) -> Result[ParseSuccess[U], ParseError]:
            result = self.parse(input)
            if result.is_ok():
                value, rest = result.unwrap()
                return Ok((f(value), rest))
            return result
        return Parser(new_parser, f"{self.name}.map")

    def then[U](self, f: 'Parser[U]') -> 'Parser[Tuple[T, U]]':
        """Apply the current parser, then apply the next parser, returning a tuple of both outputs."""
        def new_parser(input: str) -> Result[ParseSuccess[Tuple[T, U]], ParseError]:
            result = self.parse(input)
            if result.is_ok():
                v1, rest = result.unwrap()
                return f(rest).map(lambda res: ((v1, res[0]), res[1]))
            return result
        return Parser(new_parser, f"{self.name}.then({f.name})")
    
    def ignore_then[U](self, f: 'Parser[U]') -> 'Parser[U]':
        """Apply the current parser, then apply the next parser, returning the output of the next parser."""
        return self.then(f).map(lambda x: x[1])
    
    def then_ignore[U](self, f: 'Parser[U]') -> 'Parser[T]':
        """Apply the current parser, then apply the next parser, returning the output of the current parser."""
        return self.then(f).map(lambda x: x[0])
    
    def or_else[U](self, f: 'Parser[U]') -> 'Parser[Union[T, U]]':
        """Apply the current parser, if it fails, apply the next parser."""
        def new_parser(input: str) -> Result[ParseSuccess[Union[T, U]], ParseError]:
            result = self.parse(input)
            if result.is_err():
                return f(input)
            return result
        return Parser(new_parser, f"{self.name}.or_else({f.name})")
    
    def padded(self) -> 'Parser[T]':
        """Skip leading whitespace before applying the parser."""
        def new_parser(input: str) -> Result[ParseSuccess[T], ParseError]:
            input = input.lstrip()
            return self.parse(input)
        return Parser(new_parser, f"{self.name}.padded()")
    
    def between(self, d1: 'Parser[Any]', d2: 'Parser[Any]') -> 'Parser[T]':
        """Parse a delimiter, then parse the value, then parse another delimiter."""
        return d1.ignore_then(self).then_ignore(d2).label(f"{self.name}.between({d1.name}, {d2.name})")
    
    def sep_by(self, delimiter: 'Parser[Any]') -> 'Parser[List[T]]':
        """Parse a list of values separated by a delimiter."""
        def new_parser(input: str) -> Result[ParseSuccess[List[T]], ParseError]:
            values = []
            rest = input

            result = self.parse(input)
            while result.is_ok():
                value, rest = result.unwrap()
                values.append(value)
                result = delimiter.ignore_then(self).parse(rest)
            return Ok((values, rest))
        return Parser(new_parser, f"{self.name}.sep_by({delimiter.name})")
    
    def repeated(self) -> 'Parser[List[T]]':
        """Repeat the parser until it fails."""
        def new_parser(input: str) -> Result[ParseSuccess[List[T]], ParseError]:
            values = []
            rest = input

            result = self.parse(rest)
            while result.is_ok():
                value, rest = result.unwrap()
                values.append(value)
                result = self.parse(rest)
                
            return Ok((values, rest))
        return Parser(new_parser, f"{self.name}.repeated()")
    
    def or_not(self) -> 'Parser[Union[T, None]]':
        """Apply the parser, if it fails, return None."""
        def new_parser(input: str) -> Result[ParseSuccess[Union[T, None]], ParseError]:
            result = self.parse(input)
            if result.is_ok():
                return result
            return Ok((None, input))
        return Parser(new_parser, f"or_not({self.name})")
    
    def eof(self) -> 'Parser[T]':
        """Apply the parser, then check if the input is empty."""
        def new_parser(input: str) -> Result[ParseSuccess[T], ParseError]:
            result = self.parse(input)
            if result.is_ok() and not result.unwrap()[1]:
                return result
            return Err(f"Expected EOF, found {result}")
        return Parser(new_parser, f"{self.name}.eof()")
    
    @staticmethod
    def char(f: Callable[[str], bool], name: str = "char") -> 'Parser[str]':
        """Parse a character that satisfies the condition."""
        def new_parser(input: str) -> Result[ParseSuccess[str], ParseError]:
            if input and f(input[0]):
                return Ok((input[0], input[1:]))
            return Err(f"Expected a character that satisfies the condition, found '{input}'")
        return Parser(new_parser, name)
    
    @staticmethod
    def just(token: str) -> 'Parser[str]':
        """Parse a specific string. Returns the string if it matches."""
        def new_parser(input: str) -> Result[ParseSuccess[str], ParseError]:
            if input.startswith(token):
                return Ok((token, input[len(token):]))
            return Err(f"Expected '{token}', found '{input[:len(token) + 5]}'")
        return Parser(new_parser, f"just('{token}')")
    
    @staticmethod
    def accumulate_while(f: Callable[[str], bool]) -> 'Parser[str]':
        """Collect characters from the input until the condition returns false. Then return the collected characters."""
        def new_parser(input: str) -> Result[ParseSuccess[str], ParseError]:
            collected = ""
            for c in input:
                if f(c):
                    collected += c
                else:
                    break
            return Ok((collected, input[len(collected):]))
        return Parser(new_parser, "accumulate_while")

    @staticmethod
    def number() -> 'Parser[int]':
        """Parse a number."""
        def new_parser(input: str) -> Result[ParseSuccess[int], ParseError]:
            result = Parser.accumulate_while(lambda c: c.isdigit())(input)
            if result.is_ok() and result.unwrap()[0]:
                num, rest = result.unwrap()
                return Ok((int(num), rest))
            return Err(f"Expected a number, found '{input}'")
        return Parser(new_parser, "number")
    
    @staticmethod
    def ident() -> 'Parser[str]':
        """Parse an ident. An ident starts with a letter and is followed by alphanumeric characters."""
        def new_parser(input: str) -> Result[ParseSuccess[str], ParseError]:
            word = ""
            for c in input:
                if (word == "" and c.isalpha()) or (word != "" and c.isalnum()):
                    word += c
                else:
                    break
            if word:
                return Ok((word, input[len(word):]))
            return Err(f"Expected a word, found '{input}'")
        return Parser(new_parser, "ident")
    
    @staticmethod
    def recursive(parser_fn: Callable[['Parser[T]'], 'Parser[T]']) -> 'Parser[T]':
        """Pass a function that returns a parser given the parser it should return."""
        cell = [None] # mutability goes brrr
        parser = Parser(lambda input: cell[0](input))
        cell[0] = lambda input: parser_fn(parser)(input)

        return parser.label("recursive")

# Example library usage:
#
# A parser that parses a number, then a comma, then a number with any amount of spaces between them.

# print(Parser.number().padded().then_ignore(Parser.just(",").padded()).then(Parser.number().padded()).parse("  1 , 2"))

# Example usage with debug:
# Parser.enable_debug()
# number = Parser.number().with_name("number")
# comma = Parser.just(",").padded().with_name("comma")
# parser = number.padded().then_ignore(comma).then(number.padded())
# result = parser.parse("  1 , 2")
# Parser.disable_debug()