import os
import sqlite3
import tempfile
from fastapi.testclient import TestClient

# Set environment variable before importing main
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")

import main
from unittest.mock import AsyncMock


class MockResponse:
    def __init__(self, data):
        self._data = data
    def json(self):
        return self._data


def create_client(tmp_path):
    # use temporary database
    db_file = tmp_path / "test.db"
    main.DB_PATH = str(db_file)

    async def mock_post(self, url, headers=None, json=None):
        return MockResponse({"choices": [{"message": {"content": "mocked"}}]})

    # patch httpx.AsyncClient.post
    main.httpx.AsyncClient.post = AsyncMock(side_effect=mock_post)

    return TestClient(main.app)


def test_ask_endpoint(tmp_path):
    client = create_client(tmp_path)
    with client:
        response = client.post("/ask", json={"question": "hello"})
        assert response.status_code == 200
        assert response.json()["response"] == "mocked"

    # verify question stored in database
    conn = sqlite3.connect(main.DB_PATH)
    row = conn.execute("SELECT question FROM prompts").fetchone()
    conn.close()
    assert row[0] == "hello"
