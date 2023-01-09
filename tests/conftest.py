import pytest


@pytest.fixture
def fixture5() -> int:
    return 41


@pytest.fixture
def fixture6(fixture5) -> int:
    return fixture5


@pytest.fixture
def fixture1() -> int:
    return 83
