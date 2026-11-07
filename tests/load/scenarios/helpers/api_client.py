import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen


@dataclass
class ZippApiClient:
  http_client: Any
  base_url: str
  client_id: str
  username: str
  password: str
  access_token: str | None = None

  def login(self) -> str | None:
    request = Request(
        os.environ.get(
            "COGNITO_API_URL", "https://cognito-idp.ap-south-2.amazonaws.com/"
        ),
        data=json.dumps(
            {
              "AuthFlow": "USER_PASSWORD_AUTH",
              "ClientId": self.client_id,
              "AuthParameters": {
                "USERNAME": self.username,
                "PASSWORD": self.password,
              },
            }
        ).encode(),
        headers={
          "Content-Type": "application/x-amz-json-1.1",
          "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        },
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
      result = json.load(response)
    try:
      self.access_token = result["AuthenticationResult"]["AccessToken"]
    except (KeyError, TypeError) as error:
      raise RuntimeError(
          "Cognito authentication did not return an access token "
          f"(challenge: {result.get('ChallengeName', 'unknown')})"
      ) from error
    return self.access_token

  def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
    if not self.access_token:
      raise RuntimeError("Call login() before requesting authenticated APIs")
    headers = {"Authorization": f"Bearer {self.access_token}"}
    headers.update(extra or {})
    return headers

  def create_link(self, payload: dict[str, Any]):
    return self.http_client.post("/link/", json=payload, headers=self._headers())

  def list_links(self, limit: int = 100, offset: int = 0):
    return self.http_client.get(
        f"/links?limit={limit}&offset={offset}", headers=self._headers()
    )

  def get_link(self, short_code: str):
    return self.http_client.get(f"/links/{short_code}", headers=self._headers())

  def visit_link(self, short_code: str, headers: dict[str, str] | None = None):
    return self.http_client.get(
        f"/link/{short_code}", headers=headers or {}, allow_redirects=False
    )

  def update_link(self, short_code: str, url: str):
    return self.http_client.patch(
        f"/links/{short_code}", json={"url": url}, headers=self._headers()
    )

  def disable_link(self, short_code: str):
    return self.http_client.delete(f"/links/{short_code}", headers=self._headers())
