import random

from helpers.api_client import ZippApiClient
from helpers.utils import Utils
from locust import HttpUser, between, task


class WriteHeavyLinkCreationUser(HttpUser):
    """Create links continuously across policy, TTL, and title variants."""

    wait_time = between(0.2, 0.8)
    api_client: ZippApiClient

    POLICY_PROFILES = ("public", "password_protected", "ip_restricted", "limited")
    POLICY_WEIGHTS = (60, 20, 10, 10)
    TTL_PROFILES = (300, 3600, 86400, 2592000)
    TTL_WEIGHTS = (15, 25, 40, 20)

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

    @task
    def create_link(self) -> None:
        profile = random.choices(
            self.POLICY_PROFILES,
            weights=self.POLICY_WEIGHTS,
            k=1,
        )[0]
        ttl_seconds = random.choices(
            self.TTL_PROFILES,
            weights=self.TTL_WEIGHTS,
            k=1,
        )[0]

        policy: dict[str, object]
        if profile == "password_protected":
            policy = {
                "type": "password_protected",
                "password": "load-test-password",
            }
        elif profile == "ip_restricted":
            policy = {
                "type": "ip_restricted",
                "ip_list": ["0.0.0.0/0", "::/0"],
            }
        else:
            policy = {"type": "public"}

        payload: dict[str, object] = {
            "url": f"{self.host.rstrip('/')}/dummy-target",
            "ttl_seconds": ttl_seconds,
            "short_code": Utils.generate_code(),
            "policy": policy,
        }
        if random.random() < 0.75:
            payload["title"] = f"write-{profile}-{Utils.random_string()}"
        if profile == "limited":
            payload["max_visits"] = random.choice((100, 1000, 10000))

        self.api_client.create_link(
            payload,
            name=f"POST /link/ [{profile}]",
        )
