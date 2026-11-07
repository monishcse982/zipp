import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.db.session import status_check as database_status_check
from app.kafka.producer import kafka_producer

router = APIRouter(tags=["Health"], prefix="/health")
logger = logging.getLogger(__name__)


async def redis_status_check(redis: Redis) -> bool:
  try:
    return bool(await asyncio.wait_for(redis.ping(), timeout=1))
  except (RedisError, TimeoutError):
    logger.exception("Redis health check failed")
    return False


async def kafka_status_check() -> bool:
  try:
    return await asyncio.wait_for(
        asyncio.to_thread(kafka_producer.is_available),
        timeout=40,
    )
  except TimeoutError:
    logger.exception("Kafka health check failed")
    return False


@router.get("/live")
async def live() -> dict[str, str]:
  return {"status": "ok"}


@router.get("/ready")
async def health(request: Request) -> dict[str, Any]:
  database, redis, kafka = await asyncio.gather(
      database_status_check(),
      redis_status_check(request.app.state.cache),
      kafka_status_check(),
      return_exceptions=True,
  )
  checks = {
    "database": database is True,
    "redis": redis is True,
    "kafka": kafka is True,
  }
  response = {
    "status": "ready" if all(checks.values()) else "not_ready",
    "checks": {
      name: "ok" if passed else "unavailable"
      for name, passed in checks.items()
    },
  }
  if response["status"] != "ready":
    raise HTTPException(status_code=503, detail=response)
  return response
