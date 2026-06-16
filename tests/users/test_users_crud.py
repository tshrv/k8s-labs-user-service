import pytest
from httpx import AsyncClient

BASE = "/api/v1/users"

USER_PAYLOAD = {
    "email": "alice@example.com",
    "username": "alice",
    "full_name": "Alice Example",
    "password": "supersecret1",
}


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient) -> None:
    response = await client.post(BASE, json=USER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == USER_PAYLOAD["email"]
    assert data["username"] == USER_PAYLOAD["username"]
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient) -> None:
    await client.post(BASE, json=USER_PAYLOAD)
    response = await client.post(BASE, json=USER_PAYLOAD)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient) -> None:
    created = await client.post(BASE, json=USER_PAYLOAD)
    user_id = created.json()["id"]

    response = await client.get(f"{BASE}/{user_id}")
    assert response.status_code == 200
    assert response.json()["id"] == user_id


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient) -> None:
    await client.post(BASE, json=USER_PAYLOAD)
    response = await client.get(BASE)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient) -> None:
    response = await client.get(BASE, params={"page": 1, "size": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 1
    assert data["page"] == 1
    assert data["size"] == 1


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient) -> None:
    created = await client.post(BASE, json=USER_PAYLOAD)
    user_id = created.json()["id"]

    response = await client.patch(f"{BASE}/{user_id}", json={"full_name": "Alice Updated"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Alice Updated"


@pytest.mark.asyncio
async def test_update_user_not_found(client: AsyncClient) -> None:
    response = await client.patch(f"{BASE}/nonexistent-id", json={"full_name": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient) -> None:
    created = await client.post(BASE, json=USER_PAYLOAD)
    user_id = created.json()["id"]

    response = await client.delete(f"{BASE}/{user_id}")
    assert response.status_code == 204

    response = await client.get(f"{BASE}/{user_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient) -> None:
    response = await client.delete(f"{BASE}/nonexistent-id")
    assert response.status_code == 404
