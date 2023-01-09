import inspect
import sys
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Callable, Iterable, Optional, Sequence, TypeVar, Union, overload

import pytest
from typing_extensions import Literal, dataclass_transform

T = TypeVar("T", bound=type)

_ScopeName = Literal["session", "package", "module", "class", "function"]


@overload
def fixture_class(
    fixture_cls: T,
    *,
    scope: "Union[_ScopeName, Callable[[str, pytest.Config], _ScopeName]]" = ...,
    params: Optional[Iterable[object]] = ...,
    autouse: bool = ...,
    ids: Optional[Union[Sequence[Optional[object]], Callable[[Any], Optional[object]]]] = ...,
    name: Optional[str] = ...,
) -> T:
    ...


@overload
def fixture_class(
    fixture_cls: None = ...,
    *,
    scope: "Union[_ScopeName, Callable[[str, pytest.Config], _ScopeName]]" = ...,
    params: Optional[Iterable[object]] = ...,
    autouse: bool = ...,
    ids: Optional[Union[Sequence[Optional[object]], Callable[[Any], Optional[object]]]] = ...,
    name: Optional[str] = None,
) -> Callable[[T], T]:
    ...


@dataclass_transform(eq_default=False, order_default=False, kw_only_default=False)
def fixture_class(
    fixture_cls=None,
    *,
    scope: "Union[_ScopeName, Callable[[str, pytest.Config], _ScopeName]]" = "function",
    params: Optional[Iterable[object]] = None,
    autouse: bool = False,
    ids: Optional[Union[Sequence[Optional[object]], Callable[[Any], Optional[object]]]] = None,
    name: Optional[str] = None,
) -> Union[T, Callable[[T], T]]:
    def inner(fixture_cls):
        kwargs = {"slots": True} if sys.version_info >= (3, 10) else {}
        fixture_dataclass = dataclass(frozen=True, repr=False, eq=False, **kwargs)(fixture_cls)
        args = list(inspect.signature(fixture_dataclass.__init__).parameters)[1:]
        func_def = dedent(
            f"""
            def {fixture_dataclass.__name__}({', '.join(args)}):
                return fixture_cls({', '.join(args)})
        """
        )
        namespace = {"fixture_cls": fixture_dataclass}
        exec(func_def, namespace)
        func = namespace[fixture_dataclass.__name__]
        func.__module__ = fixture_cls.__module__
        func.__doc__ = fixture_cls.__doc__ or fixture_dataclass.__doc__
        return pytest.fixture(scope=scope, params=params, autouse=autouse, ids=ids, name=name)(func)

    return inner if fixture_cls is None else inner(fixture_cls)
