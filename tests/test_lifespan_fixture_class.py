import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from pytest_fixture_classes import fixture_class

execution_log: list[str] = []


@pytest.fixture(autouse=True)
def reset_execution_log():
    execution_log.clear()


@pytest.fixture
def sync_fixture() -> int:
    return 100


@pytest_asyncio.fixture
async def async_fixture() -> int:
    await asyncio.sleep(0)
    return 2


@fixture_class(name="sync_lifespan_factory")
class SyncLifespanFactory:
    sync_fixture: int

    def lifespan(self) -> Generator:
        execution_log.append("sync_factory_init")
        yield
        execution_log.append("sync_factory_cleanup")

    def __call__(self, value: int) -> int:
        return value * self.sync_fixture


@fixture_class(name="async_lifespan_factory")
class AsyncLifespanFactory:
    sync_fixture: int
    async_fixture: int

    async def lifespan(self) -> AsyncGenerator:
        execution_log.append("async_factory_init")
        yield
        execution_log.append("async_factory_cleanup")

    async def __call__(self, value: int) -> int:
        return value * self.sync_fixture + self.async_fixture


def test_sync_lifespan_factory(sync_lifespan_factory: SyncLifespanFactory) -> None:
    assert "sync_factory_init" in execution_log

    assert sync_lifespan_factory(1) == 100
    assert sync_lifespan_factory(2) == 200
    assert sync_lifespan_factory(3) == 300

    assert "sync_factory_cleanup" not in execution_log


@pytest.mark.asyncio
async def test_async_lifespan_factory(
    async_lifespan_factory: AsyncLifespanFactory,
) -> None:
    assert "async_factory_init" in execution_log

    assert await async_lifespan_factory(1) == 102
    assert await async_lifespan_factory(2) == 202
    assert await async_lifespan_factory(3) == 302

    assert "async_factory_cleanup" not in execution_log
