"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_messages():
    return [{"role": "user", "content": "What products do you have?"}]
