import inspect
import sys
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from dataclasses import dataclass
from functools import partial
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Generator,
    Iterable,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)

import pytest
from typing_extensions import Literal, ParamSpec, dataclass_transform

T = TypeVar("T", bound=type)
R = TypeVar("R")
P = ParamSpec("P")

_ScopeName = Literal["session", "package", "module", "class", "function"]


@overload
def yield_fixture(
    func: Callable[P, Generator[R, None, None]],
) -> Callable[P, R]: ...


@overload
def yield_fixture(
    func: Callable[P, AsyncGenerator[R, None]],
) -> Callable[P, Coroutine[Any, Any, R]]: ...


def yield_fixture(func: Callable[..., Any]) -> Callable[..., Any]:
    """Type a generator __call__ by its yielded value inside a fixture class."""
    return func


def _yield_fixture(
    fixture_cls: Type[Any], *dependencies: Any
) -> Generator[Any, None, None]:
    with ExitStack() as stack:

        def call(self: Any, *args: Any, **kwargs: Any) -> Any:
            context = contextmanager(fixture_cls.__call__)(self, *args, **kwargs)
            value = context.__enter__()
            stack.callback(context.__exit__, None, None, None)
            return value

        @dataclass(init=False, frozen=True, repr=False, eq=False)
        class ManagedFixture(fixture_cls):  # type: ignore[valid-type, misc]
            __slots__ = ()
            __module__ = fixture_cls.__module__
            __doc__ = fixture_cls.__doc__
            __call__ = call

        yield ManagedFixture(*dependencies)


async def _async_yield_fixture(
    fixture_cls: Type[Any], *dependencies: Any
) -> AsyncGenerator[Any, None]:
    async with AsyncExitStack() as stack:

        async def call(self: Any, *args: Any, **kwargs: Any) -> Any:
            context = asynccontextmanager(fixture_cls.__call__)(self, *args, **kwargs)
            value = await context.__aenter__()
            stack.push_async_callback(context.__aexit__, None, None, None)
            return value

        @dataclass(init=False, frozen=True, repr=False, eq=False)
        class ManagedFixture(fixture_cls):  # type: ignore[valid-type, misc]
            __slots__ = ()
            __module__ = fixture_cls.__module__
            __doc__ = fixture_cls.__doc__
            __call__ = call

        yield ManagedFixture(*dependencies)


@overload
def fixture_class(
    fixture_cls: T,
    *,
    scope: "Union[_ScopeName, Callable[[str, pytest.Config], _ScopeName]]" = ...,
    params: Optional[Iterable[object]] = ...,
    autouse: bool = ...,
    ids: Optional[
        Union[Sequence[Optional[object]], Callable[[Any], Optional[object]]]
    ] = ...,
    name: Optional[str] = ...,
) -> T: ...


@overload
def fixture_class(
    fixture_cls: None = ...,
    *,
    scope: "Union[_ScopeName, Callable[[str, pytest.Config], _ScopeName]]" = ...,
    params: Optional[Iterable[object]] = ...,
    autouse: bool = ...,
    ids: Optional[
        Union[Sequence[Optional[object]], Callable[[Any], Optional[object]]]
    ] = ...,
    name: Optional[str] = None,
) -> Callable[[T], T]: ...


@dataclass_transform(eq_default=False, order_default=False, kw_only_default=False)
def fixture_class(
    fixture_cls=None,
    *,
    scope: "Union[_ScopeName, Callable[[str, pytest.Config], _ScopeName]]" = "function",
    params: Optional[Iterable[object]] = None,
    autouse: bool = False,
    ids: Optional[
        Union[Sequence[Optional[object]], Callable[[Any], Optional[object]]]
    ] = None,
    name: Optional[str] = None,
) -> Union[T, Callable[[T], T]]:
    def inner(fixture_cls):
        kwargs = {"slots": True} if sys.version_info >= (3, 10) else {}
        fixture_dataclass = dataclass(frozen=True, repr=False, eq=False, **kwargs)(
            fixture_cls
        )
        args = list(inspect.signature(fixture_dataclass.__init__).parameters)[1:]
        namespace = {"fixture_cls": fixture_dataclass}
        call = getattr(fixture_dataclass, "__call__", None)
        is_async_generator = inspect.isasyncgenfunction(call)
        call_args = ", ".join(args)

        if is_async_generator:
            namespace["fixture_cls"] = partial(_async_yield_fixture, fixture_dataclass)
            body = (
                f"async for instance in fixture_cls({call_args}):\n"
                "        yield instance"
            )
        elif inspect.isgeneratorfunction(call):
            namespace["fixture_cls"] = partial(_yield_fixture, fixture_dataclass)
            body = f"yield from fixture_cls({call_args})"
        else:
            body = f"return fixture_cls({call_args})"

        func_def = (
            f"{'async ' if is_async_generator else ''}"
            f"def {fixture_dataclass.__name__}({call_args}):\n"
            f"    {body}\n"
        )
        exec(func_def, namespace)
        func = namespace[fixture_dataclass.__name__]
        func.__module__ = fixture_cls.__module__
        func.__doc__ = fixture_cls.__doc__ or fixture_dataclass.__doc__
        return pytest.fixture(
            scope=scope, params=params, autouse=autouse, ids=ids, name=name
        )(func)

    return inner if fixture_cls is None else inner(fixture_cls)
