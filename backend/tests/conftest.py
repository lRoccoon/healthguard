"""
Shared test fixtures and configuration.
"""

import pytest
import os

# Set test environment variables before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOCAL_STORAGE_PATH", "/tmp/healthguard_test_data")


@pytest.fixture
def anyio_backend():
    return "asyncio"
