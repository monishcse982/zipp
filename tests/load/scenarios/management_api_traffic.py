import random

from helpers.api_client import ZippApiClient
from helpers.utils import Utils
from locust import HttpUser, between, task


class ManagementApiTrafficUser(HttpUser):
    """Exercise authenticated link-management operations with read-heavy traffic."""

    wait_time = between(0.5, 1.5)
    api_client: ZippApiClient
    short_codes: list[str]

    def on_start(self) -> None:
        if self.host is None:
            raise RuntimeError("Invalid host configured in load tests")

        self.api_client = ZippApiClient(
            http_client=self.client,
            base_url=self.host.rstrip("/"),
            client_id=Utils.required_env("COGNITO_CLIENT_ID"),
            username=Utils.required_env("COGNITO_API_USERNAME"),
            password=Utils.required_env("COGNITO_API_PASSWORD"),
        )
        self.api_client.login()
        self.short_codes = [self._create_link(setup=True) for _ in range(3)]

    def _create_link(self, *, setup: bool = False) -> str:
        payload = {
            "url": f"{self.host.rstrip('/')}/dummy-target",
            "ttl_seconds": 86400,
            "title": f"management-{Utils.random_string()}",
            "short_code": Utils.generate_code(),
            "policy": {"type": "public"},
        }
        request_name = "POST /link/ [setup]" if setup else "POST /link/ [management]"
        response = self.api_client.create_link(payload, name=request_name)
        if response.status_code != 200:
            raise RuntimeError(
                f"Management link creation failed with {response.status_code}"
            )
        return response.json()["shortened_url"].rstrip("/").split("/")[-1]

    def _random_short_code(self) -> str:
        if not self.short_codes:
            self.short_codes.append(self._create_link(setup=True))
        return random.choice(self.short_codes)

    @task(65)
    def list_links(self) -> None:
        self.api_client.list_links(limit=100, offset=0)

    @task(20)
    def get_link_details(self) -> None:
        self.api_client.get_link(self._random_short_code())

    @task(8)
    def create_link(self) -> None:
        self.short_codes.append(self._create_link())

    @task(5)
    def update_link(self) -> None:
        short_code = self._random_short_code()
        destination = (
            f"{self.host.rstrip('/')}/dummy-target?revision={Utils.random_string(8)}"
        )
        self.api_client.update_link(short_code, destination)

    @task(2)
    def disable_link(self) -> None:
        short_code = self._random_short_code()
        response = self.api_client.disable_link(short_code)
        if response.status_code == 204:
            self.short_codes.remove(short_code)
            self.short_codes.append(self._create_link(setup=True))
