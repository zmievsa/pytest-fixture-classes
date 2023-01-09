from .test_fixture_class import Fixture2, Fixture3


def test_another_file(fixture1, fixture3: Fixture3):
    """This test verifies that fixture3 can be discovered in another file."""
    assert fixture1 == fixture3() == 83
