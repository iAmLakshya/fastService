import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_todo(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/todos",
        json={"title": "Test Todo", "description": "Test description"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "Test description"
    assert data["completed"] is False
    assert "id" in data


@pytest.mark.anyio
async def test_list_todos(client: AsyncClient) -> None:
    await client.post("/api/v1/todos", json={"title": "Todo 1"})
    await client.post("/api/v1/todos", json={"title": "Todo 2"})

    response = await client.get("/api/v1/todos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.anyio
async def test_get_todo(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/todos", json={"title": "Get Me"})
    todo_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Get Me"


@pytest.mark.anyio
async def test_get_todo_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/todos/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_todo(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/todos", json={"title": "Update Me"})
    todo_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated", "completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["completed"] is True


@pytest.mark.anyio
async def test_delete_todo(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/todos", json={"title": "Delete Me"})
    todo_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/todos/{todo_id}")
    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/todos/{todo_id}")
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_filter_todos_by_completed(client: AsyncClient) -> None:
    await client.post("/api/v1/todos", json={"title": "Incomplete"})
    create_response = await client.post("/api/v1/todos", json={"title": "Complete"})
    todo_id = create_response.json()["id"]
    await client.patch(f"/api/v1/todos/{todo_id}", json={"completed": True})

    response = await client.get("/api/v1/todos", params={"completed": True})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["completed"] is True


@pytest.mark.anyio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
