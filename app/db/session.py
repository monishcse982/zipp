import asyncio
import logging

from asyncpg import PostgresError
from tortoise import Tortoise
from tortoise.exceptions import ConfigurationError, DBConnectionError

from app.core.config import settings, tortoise_database_url

logger = logging.getLogger(__name__)


async def init_db() -> None:
  await Tortoise.init(
      db_url=tortoise_database_url(settings.database_url),
      modules={"models": ["app.db.models"]},
      use_tz=True,
      timezone="UTC",
      _enable_global_fallback=True,
  )


async def status_check() -> bool:
  try:
    connection = Tortoise.get_connection("default")
    result = await asyncio.wait_for(
        connection.execute_query("SELECT 1"),
        timeout=1,
    )
    return bool(result)
  except (ConfigurationError, DBConnectionError, PostgresError, TimeoutError):
    logger.exception("Database readiness check failed")
    return False


async def close_db() -> None:
  await Tortoise.close_connections()
