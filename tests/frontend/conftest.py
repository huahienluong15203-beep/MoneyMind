import os
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")

@pytest.fixture(scope="session")
def base_url():
    """URL cơ sở của server MoneyMind phục vụ kiểm thử E2E"""
    return BASE_URL

@pytest.fixture(scope="function")
def test_user_credentials():
    return {
        "email": "test_e2e_user@example.com",
        "password": "Password123!",
        "full_name": "Test E2E User"
    }
