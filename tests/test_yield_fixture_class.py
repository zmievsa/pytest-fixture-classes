"""Verify generator fixture values, teardown, failures, and module scope."""

import asyncio
from dataclasses import FrozenInstanceError
from typing import AsyncGenerator, Awaitable, Generator, List, Union, cast

import pytest

from pytest_fixture_classes import fixture_class, yield_fixture
from pytest_fixture_classes.fixture_class import (_async_yield_fixture,
                                                  _yield_fixture)


class _Factory:
    """Share an event log with frozen generator fixture instances."""

    events: List[str]

    def __init__(self, events: List[str]) -> None:
        object.__setattr__(self, "events", events)


class _SyncFactory(_Factory):
    """Synchronous factory used by fixtures and direct lifecycle tests."""

    @yield_fixture
    def __call__(
        self, name: str, *, yields: int = 1, cleanup_error: bool = False
    ) -> Generator[str, None, None]:
        yield from generate(self.events, name, yields, cleanup_error)


class _AsyncFactory(_Factory):
    """Async factory that awaits during setup and teardown."""

    @yield_fixture
    async def __call__(
        self, name: str, *, yields: int = 1, cleanup_error: bool = False
    ) -> AsyncGenerator[str, None]:
        for value in generate(self.events, name, yields, cleanup_error):
            await asyncio.sleep(0)
            yield value
            await asyncio.sleep(0)


@fixture_class(name="make_resource")
class MakeResource(_SyncFactory):
    """Inject the event log into a synchronous generator factory."""

    events: List[str]


@fixture_class(name="make_async_resource")
class MakeAsyncResource(_AsyncFactory):
    """Inject the event log into an async generator factory."""

    events: List[str]


@fixture_class(name="module_factory", scope="module")
class ModuleFactory:
    """Keep generated resources alive until module teardown."""

    module_events: List[str]

    @yield_fixture
    def __call__(self, name: str) -> Generator[str, None, None]:
        yield from generate(self.module_events, name)


Factory = Union[_SyncFactory, _AsyncFactory]
Lifecycle = Union[Generator[Factory, None, None], AsyncGenerator[Factory, None]]


def generate(
    events: List[str], name: str, yields: int = 1, cleanup_error: bool = False
) -> Generator[str, None, None]:
    """Log setup and cleanup with configurable yield counts and failures."""
    events.append(name)
    for _ in range(yields):
        yield name
    events.append(f"cleanup:{name}")
    if cleanup_error:
        raise RuntimeError("cleanup failed")


def event_log() -> Generator[List[str], None, None]:
    """Require setup events followed by cleanup events in reverse order."""
    events: List[str] = []
    yield events
    names = [event for event in events if not event.startswith("cleanup:")]
    assert events == names + [f"cleanup:{name}" for name in reversed(names)]


async def resolve(value: Union[str, Awaitable[str]]) -> str:
    """Return a synchronous result or await an asynchronous result."""
    return value if isinstance(value, str) else await value


async def close_lifecycle(lifecycle: Lifecycle) -> None:
    """Finalize a fixture generator to inspect its teardown errors."""
    if isinstance(lifecycle, Generator):
        lifecycle.close()
    else:
        await lifecycle.aclose()


@pytest.fixture
def events() -> Generator[List[str], None, None]:
    """Provide an event log and verify cleanup after each test."""
    yield from event_log()


@pytest.fixture(params=["make_resource", "make_async_resource"])
def factory(request: pytest.FixtureRequest) -> Factory:
    """Select the synchronous or asynchronous fixture class."""
    return cast(Factory, request.getfixturevalue(request.param))


@pytest.fixture(params=["sync", "async"])
async def lifecycle(request: pytest.FixtureRequest) -> AsyncGenerator[Lifecycle, None]:
    """Expose either fixture generator for direct teardown assertions."""
    iterator: Lifecycle = (
        _yield_fixture(_SyncFactory, [])
        if request.param == "sync"
        else _async_yield_fixture(_AsyncFactory, [])
    )
    yield iterator
    await close_lifecycle(iterator)


@pytest.fixture(scope="module")
def module_events() -> Generator[List[str], None, None]:
    """Share an event log across tests and verify cleanup at module end."""
    yield from event_log()


@pytest.mark.parametrize(
    "fail_test",
    [
        False,
        pytest.param(True, marks=pytest.mark.xfail(strict=True, raises=RuntimeError)),
    ],
    ids=["success", "failed-test"],
)
@pytest.mark.asyncio
async def test_yield_fixture_class(
    factory: Factory, events: List[str], fail_test: bool
) -> None:
    """Return yielded values and defer cleanup, including after test failure."""
    assert await resolve(factory("first")) == "first"
    assert await resolve(factory(name="second")) == "second"
    assert events == ["first", "second"]
    if fail_test:
        raise RuntimeError("Deliberate test failure to verify fixture cleanup")


@pytest.mark.asyncio
async def test_no_yield(factory: Factory) -> None:
    """Reject a factory call whose generator yields no value."""
    with pytest.raises(RuntimeError, match="generator didn't yield"):
        await resolve(factory("resource", yields=0))


@pytest.mark.asyncio
async def test_factory_immutability(factory: Factory) -> None:
    """Reject additions, changes, and deletions of fixture attributes."""
    for name in ("extra", "events"):
        with pytest.raises(FrozenInstanceError):
            setattr(factory, name, [])
        with pytest.raises(FrozenInstanceError):
            delattr(factory, name)


@pytest.mark.parametrize(
    "yields, cleanup_error, message",
    [(1, True, "cleanup failed"), (2, False, "generator didn't stop")],
)
@pytest.mark.asyncio
async def test_teardown_error_keeps_cleaning(
    lifecycle: Lifecycle, yields: int, cleanup_error: bool, message: str
) -> None:
    """Run the remaining cleanups in reverse order after a teardown error."""
    factory = (
        next(lifecycle)
        if isinstance(lifecycle, Generator)
        else await lifecycle.__anext__()
    )
    await resolve(factory("first"))
    await resolve(factory("second", yields=yields, cleanup_error=cleanup_error))
    await resolve(factory("third"))
    with pytest.raises(RuntimeError, match=message):
        await close_lifecycle(lifecycle)
    cleaned = ["third", "second", "first"] if cleanup_error else ["third", "first"]
    assert factory.events == ["first", "second", "third"] + [
        f"cleanup:{name}" for name in cleaned
    ]


@pytest.mark.parametrize("name", ["first", "second"])
def test_module_scope(
    module_factory: ModuleFactory, module_events: List[str], name: str
) -> None:
    """Keep module-scoped resources live across parameterized test cases."""
    previous = list(module_events)
    assert not any(event.startswith("cleanup:") for event in previous)
    assert module_factory(name) == name
    assert module_events == previous + [name]
