import os
import sqlite3
import importlib
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")


class MockResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def reload_main():
    import main
    return importlib.reload(main)


def create_client(main_module, db_path):
    main_module.DB_PATH = str(db_path)

    async def mock_post(self, url, headers=None, json=None):
        return MockResponse({"choices": [{"message": {"content": "mocked"}}]})

    main_module.httpx.AsyncClient.post = AsyncMock(side_effect=mock_post)
    return TestClient(main_module.app)


def test_ask_endpoint(tmp_path):
    main = reload_main()
    client = create_client(main, tmp_path / "test.db")
    with client:
        response = client.post("/ask", json={"question": "hello"})
        assert response.status_code == 200
        assert response.json()["response"] == "mocked"

    conn = sqlite3.connect(main.DB_PATH)
    row = conn.execute("SELECT question, answer, user FROM prompts").fetchone()
    conn.close()
    assert row[0] == "hello"
    assert row[1] == "mocked"
    assert row[2] == "testclient"


def test_db_path_from_other_cwd(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main = reload_main()
        expected = os.path.join(os.path.dirname(os.path.abspath(main.__file__)), "prompts.db")
        assert main.DB_PATH == expected

        client = create_client(main, tmp_path / "alt.db")
        with client:
            resp = client.post("/ask", json={"question": "cwd"})
            assert resp.status_code == 200

        assert os.path.exists(main.DB_PATH)
    finally:
        os.chdir(old_cwd)
        reload_main()

