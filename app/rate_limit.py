import time

import redis
from fastapi import HTTPException, status

from app.config import settings


redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def check_rate_limit(agent_id: int, limit_per_minute: int):
    current_minute = int(time.time() // 60)
    key = f"rate_limit:{agent_id}:{current_minute}"

    try:
        count = redis_client.incr(key)
        redis_client.expire(key, 60)

        if count > limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

    except redis.exceptions.RedisError:
        return