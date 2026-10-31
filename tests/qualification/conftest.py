"""Contain process-global side effects of one-shot operator helper tests."""
import os

import pytest


@pytest.fixture(autouse=True)
def preserve_operator_test_umask():
    # Production helpers deliberately tighten their one-shot process mask.
    # Pytest reuses its process; later permission-negative fixtures must retain
    # their requested modes rather than silently becoming private directories.
    original = os.umask(0o077)
    os.umask(original)
    try:
        yield
    finally:
        os.umask(original)
