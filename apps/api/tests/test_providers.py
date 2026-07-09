from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_providers():
    response = client.get("/api/providers")
    data = response.json()
    names = {provider["name"] for provider in data}

    assert response.status_code == 200
    assert {
        "mock",
        "gemini",
        "openai",
        "claude",
        "deepseek",
        "grok",
        "local_qa",
        "auto",
    }.issubset(names)
