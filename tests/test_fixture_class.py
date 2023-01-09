from pytest_fixture_classes import fixture_class


@fixture_class(name="fixture2")
class Fixture2:
    fixture1: int

    def __call__(self) -> int:
        return self.fixture1


@fixture_class(name="fixture3")
class Fixture3:
    """My Docstring"""

    fixture2: Fixture2

    def __call__(self) -> int:
        return self.fixture2()


def test_simple_fixture_usage(fixture3: Fixture3, fixture2: Fixture2, fixture1: int) -> None:
    assert fixture3() == fixture1 == 83


def test_docstring_preservation(fixture3: Fixture3) -> None:
    assert fixture3.__doc__ == "My Docstring"


def test_docstring_generation(fixture2: Fixture2) -> None:
    assert fixture2.__doc__ == "Fixture2(fixture1: int)"
