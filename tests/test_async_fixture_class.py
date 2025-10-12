import asyncio
import pytest

from pytest_fixture_classes import fixture_class


@pytest.fixture
def sync_fixture() -> int:
    return 100


@fixture_class(name="async_factory")
class AsyncFactory:
    """Async factory fixture"""
    sync_fixture: int

    async def __call__(self, multiplier: int) -> int:
        await asyncio.sleep(0)
        return self.sync_fixture * multiplier


@fixture_class(name="nested_async_factory")
class NestedAsyncFactory:
    async_factory: AsyncFactory

    async def __call__(self, value: int) -> int:
        await asyncio.sleep(0)
        return await self.async_factory(value) + 10


@pytest.mark.asyncio
async def test_async_factory(async_factory: AsyncFactory) -> None:
    assert await async_factory(1) == 100
    assert await async_factory(2) == 200
    assert await async_factory(3) == 300


@pytest.mark.asyncio
async def test_nested_async_factory(nested_async_factory: NestedAsyncFactory) -> None:
    assert await nested_async_factory(4) == 410
    assert await nested_async_factory(5) == 510
    assert await nested_async_factory(6) == 610


@pytest.mark.asyncio
async def test_async_factory_docstring_preservation(async_factory: AsyncFactory) -> None:
    assert async_factory.__doc__ == "Async factory fixture"
