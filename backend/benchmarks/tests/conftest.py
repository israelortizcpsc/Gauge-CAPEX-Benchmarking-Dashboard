import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    """The in-process cache is not rolled back with the test transaction, so
    clear it around every test to keep benchmark results from leaking."""
    cache.clear()
    yield
    cache.clear()
