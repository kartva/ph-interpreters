from typing import TypeVar, Callable, Tuple, Union, Generic, Any, Literal, TypeAlias, NoReturn

# Result type from https://github.com/rustedpy/result/blob/main/src/result/result.py

T = TypeVar("T", covariant=True)  # Success type
E = TypeVar("E", covariant=True)  # Error type
U = TypeVar("U")

class Ok(Generic[T]):
    __match_args__ = ("ok_value",)
    __slots__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def __repr__(self) -> str:
        return "Ok({})".format(repr(self._value))

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Ok) and self._value == other._value

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((True, self._value))

    def is_ok(self) -> Literal[True]:
        return True

    def is_err(self) -> Literal[False]:
        return False

    def unwrap(self) -> T:
        return self._value
    
    def map(self, op: Callable[[T], U]) -> 'Ok[U]':
        return Ok(op(self._value))
    
class Err(Generic[E]):
    """
    A value that signifies failure and which stores arbitrary data for the error.
    """

    __match_args__ = ("err_value",)
    __slots__ = ("_value",)

    def __init__(self, value: E) -> None:
        self._value = value

    def __repr__(self) -> str:
        return "Err({})".format(repr(self._value))

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Err) and self._value == other._value

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((False, self._value))

    def is_ok(self) -> Literal[False]:
        return False

    def is_err(self) -> Literal[True]:
        return True

    def unwrap(self) -> NoReturn:
        raise Exception(self._value)
    
    def map(self, op: object) -> 'Err[E]':
        return self
    
Result: TypeAlias = Union[Ok[T], Err[E]]