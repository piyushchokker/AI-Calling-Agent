import sys
from pathlib import Path
import os

import pytest
from fastapi.testclient import TestClient

# Ensure the app can import modules correctly
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Setup test environment variables
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("TENANT_API_KEY", "test_key") 

from app.main import app

@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)