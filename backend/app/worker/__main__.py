"""Worker — Redis Streams consumer for ingestion and curriculum jobs.

Run with:  python -m app.worker
Docker:    command: python -m app.worker   (in docker-compose.yml)
"""

import asyncio
import logging
import os
import signal

from app.core.db import AsyncSessionLocal
from app.core.redis import get_redis
from app.worker.curriculum import run_curriculum_job
from app.worker.pipeline import run_ingestion_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BLOCK_MS = 5000    # block for up to 5s waiting for new jobs
VISIBILITY_S = 300  # reclaim pending jobs older than 5 minutes

_CONSUMER_NAME = f"worker-{os.getpid()}"

_STREAMS = {
    "ingestion": {
        "stream_key": "ingestion.jobs",
        "group": "ingestion-workers",
        "handler": run_ingestion_pipeline,
        "log_field": "source_id",
    },
    "curriculum": {
        "stream_key": "curriculum.jobs",
        "group": "curriculum-workers",
        "handler": run_curriculum_job,
        "log_field": "path_id",
    },
}


async def _ensure_group(redis, stream_key: str, group: str) -> None:
    try:
        await redis.xgroup_create(stream_key, group, id="0", mkstream=True)
        logger.info("Created consumer group %s on %s", group, stream_key)
    except Exception:
        pass  # group already exists


async def _reclaim_stale(redis, stream_key: str, group: str) -> None:
    try:
        pending = await redis.xautoclaim(
            stream_key, group, _CONSUMER_NAME,
            min_idle_time=VISIBILITY_S * 1000,
            start_id="0-0",
            count=10,
        )
        messages = pending[1] if isinstance(pending, (list, tuple)) and len(pending) > 1 else []
        if messages:
            logger.info("Reclaimed %d stale messages from %s", len(messages), stream_key)
    except Exception as exc:
        logger.debug("xautoclaim not available or failed for %s: %s", stream_key, exc)


async def _consume_stream(stream_key: str, group: str, handler, log_field: str) -> None:
    redis = await get_redis()
    await _ensure_group(redis, stream_key, group)
    logger.info("Worker %s consuming from %s", _CONSUMER_NAME, stream_key)

    while True:
        await _reclaim_stale(redis, stream_key, group)

        messages = await redis.xreadgroup(
            group,
            _CONSUMER_NAME,
            {stream_key: ">"},
            count=1,
            block=BLOCK_MS,
        )
        if not messages:
            continue

        for _stream, entries in messages:
            for msg_id, fields in entries:
                job = {
                    k if isinstance(k, str) else k.decode(): v if isinstance(v, str) else v.decode()
                    for k, v in fields.items()
                }
                logger.info("Processing %s job %s (%s=%s)", stream_key, msg_id, log_field, job.get(log_field))
                try:
                    async with AsyncSessionLocal() as db:
                        await handler(db, job)
                    await redis.xack(stream_key, group, msg_id)
                    logger.info("Completed %s job %s", stream_key, msg_id)
                except Exception:
                    logger.exception(
                        "%s job %s failed — will be reclaimed after %ds",
                        stream_key, msg_id, VISIBILITY_S,
                    )
                    # Do NOT ack — message stays pending and will be reclaimed


def main() -> None:
    loop = asyncio.new_event_loop()

    def _shutdown(sig, frame):
        logger.info("Received %s — shutting down", sig)
        loop.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    async def _run_all():
        await asyncio.gather(
            *[
                _consume_stream(
                    cfg["stream_key"], cfg["group"], cfg["handler"], cfg["log_field"]
                )
                for cfg in _STREAMS.values()
            ]
        )

    try:
        loop.run_until_complete(_run_all())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
