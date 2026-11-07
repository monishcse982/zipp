import os
import random
import secrets
import string


class Utils:
  def __init__(self):
    super().__init__()

  @staticmethod
  def random_string(length: int = 15) -> str:
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))

  @staticmethod
  def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
      raise RuntimeError(f"{name} is required for load tests")
    return value

  @staticmethod
  def generate_code(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
