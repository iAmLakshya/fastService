from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings

_task_pool: ArqRedis | None = None


async def get_task_pool() -> ArqRedis:
    global _task_pool
    if _task_pool is None:
        redis_settings = RedisSettings.from_dsn(settings.databases.redis.url)
        _task_pool = await create_pool(redis_settings)
    return _task_pool


async def close_task_pool() -> None:
    global _task_pool
    if _task_pool is not None:
        await _task_pool.close()
        _task_pool = None


async def enqueue(
    function: str,
    *args: Any,
    _job_id: str | None = None,
    _queue_name: str | None = None,
    _defer_by: int | None = None,
    **kwargs: Any,
) -> str | None:
    if not settings.databases.redis.enabled:
        return None

    pool = await get_task_pool()
    job = await pool.enqueue_job(
        function,
        *args,
        _job_id=_job_id,
        _queue_name=_queue_name,
        _defer_by=_defer_by,
        **kwargs,
    )
    return job.job_id if job else None
