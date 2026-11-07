from helpers.api_client import ZippApiClient
from helpers.utils import Utils
from locust import HttpUser, constant, task


class MixedRedirectTrafficUser(HttpUser):
  wait_time = constant(1)
  api_client: ZippApiClient
  links: dict[str, tuple[str, dict[str, str]]]

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
    self.links = {
      "public": (self.create_link("public"), {}),
      "password": (
          self.create_link("password_protected"),
          {"password": "load-test-password"},
      ),
      "ip_restricted": (self.create_link("ip_restricted"), {}),
      "visit_limited": (self.create_link("visit_limited"), {}),
    }

  def create_link(self, link_type: str) -> str:
    policies = {
      "public": {"type": "public"},
      "password_protected": {
          "type": "password_protected",
          "password": "load-test-password",
      },
      "ip_restricted": {
          "type": "ip_restricted",
          "ip_list": ["0.0.0.0/0", "::/0"],
      },
      "visit_limited": {"type": "public"},
    }
    payload = {
      "url": f"{self.host.rstrip('/')}/dummy-target",
      "ttl_seconds": 86400,
      "title": f"load-{link_type}-{Utils.random_string()}",
      "short_code": f"{Utils.generate_code()}",
      "policy": policies[link_type],
    }
    if link_type == "visit_limited":
      payload["max_visits"] = 100000
    response = self.api_client.create_link(payload)
    if response.status_code != 200:
      raise RuntimeError(
          f"Link creation failed with {response.status_code}: {response.text}"
      )
    shortened_url = response.json()["shortened_url"]
    return shortened_url.rstrip("/").split("/")[-1]

  def visit_category(self, category: str) -> None:
    short_code, headers = self.links[category]
    with self.api_client.visit_link(short_code, headers=headers) as response:
      if response.status_code == 302:
        response.success()
      else:
        response.failure(
            f"{category} redirect returned {response.status_code}"
        )

  @task(70)
  def visit_public_link(self):
    self.visit_category("public")

  @task(15)
  def visit_password_link(self):
    self.visit_category("password")

  @task(10)
  def visit_ip_restricted_link(self):
    self.visit_category("ip_restricted")

  @task(5)
  def visit_visit_limited_link(self):
    self.visit_category("visit_limited")
