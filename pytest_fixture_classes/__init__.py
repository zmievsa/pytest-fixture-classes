try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

from .fixture_class import fixture_class

__version__ = importlib_metadata.version("pytest-fixture-classes")

__all__ = ["fixture_class", "__version__"]
