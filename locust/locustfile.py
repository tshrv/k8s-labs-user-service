import random
import string
import threading

from locust import HttpUser, between, task

# Thread-safe pool of user IDs created during the test run.
# Both MixedUser and ReadHeavyUser share this pool so read tasks always
# have valid IDs to target even before write tasks have run.
_user_id_pool: list[str] = []
_pool_lock = threading.Lock()


def _random_suffix(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


class MixedUser(HttpUser):
    """Full CRUD simulation — represents a backend service or admin client."""

    weight = 1
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        suffix = _random_suffix()
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": f"seed_{suffix}@loadtest.com",
                "username": f"seed_{suffix}",
                "full_name": f"Seed User {suffix}",
                "password": "LoadTest123!",
            },
        )
        if resp.status_code == 201:
            with _pool_lock:
                _user_id_pool.append(resp.json()["id"])

    @task(3)
    def list_users(self) -> None:
        page = random.randint(1, 5)
        size = random.choice([10, 20, 50])
        self.client.get(f"/api/v1/users?page={page}&size={size}", name="/api/v1/users")

    @task(3)
    def get_user(self) -> None:
        with _pool_lock:
            if not _user_id_pool:
                return
            user_id = random.choice(_user_id_pool)
        self.client.get(f"/api/v1/users/{user_id}", name="/api/v1/users/{id}")

    @task(2)
    def create_user(self) -> None:
        suffix = _random_suffix()
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": f"load_{suffix}@loadtest.com",
                "username": f"load_{suffix}",
                "full_name": f"Load User {suffix}",
                "password": "LoadTest123!",
            },
        )
        if resp.status_code == 201:
            with _pool_lock:
                _user_id_pool.append(resp.json()["id"])

    @task(1)
    def update_user(self) -> None:
        with _pool_lock:
            if not _user_id_pool:
                return
            user_id = random.choice(_user_id_pool)
        suffix = _random_suffix(4)
        self.client.patch(
            f"/api/v1/users/{user_id}",
            json={"full_name": f"Updated {suffix}"},
            name="/api/v1/users/{id}",
        )

    @task(1)
    def health_check(self) -> None:
        self.client.get("/api/v1/health")


class ReadHeavyUser(HttpUser):
    """Read-only simulation — represents a dashboard or reporting client."""

    weight = 3
    wait_time = between(0.2, 1.0)

    @task(5)
    def list_users(self) -> None:
        page = random.randint(1, 5)
        size = random.choice([10, 20, 50])
        self.client.get(f"/api/v1/users?page={page}&size={size}", name="/api/v1/users")

    @task(5)
    def get_user(self) -> None:
        with _pool_lock:
            if not _user_id_pool:
                return
            user_id = random.choice(_user_id_pool)
        self.client.get(f"/api/v1/users/{user_id}", name="/api/v1/users/{id}")

    @task(1)
    def health_check(self) -> None:
        self.client.get("/api/v1/health")
