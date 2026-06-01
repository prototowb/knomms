"""Ingestion worker — Redis Streams consumer.

Run with:  python -m app.worker
Docker:    command: python -m app.worker   (in docker-compose.yml)
"""

import asyncio
import logging
import os
import signal

from app.core.db import AsyncSessionLocal
from app.core.redis import get_redis
from app.worker.pipeline import run_ingestion_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STREAM_KEY = "ingestion.jobs"
CONSUMER_GROUP = "ingestion-workers"
CONSUMER_NAME = f"worker-{os.getpid()}"
BLOCK_MS = 5000    # block for up to 5s waiting for new jobs
VISIBILITY_S = 300  # reclaim pending jobs older than 5 minutes


async def _ensure_consumer_group(redis) -> None:
    try:
        await redis.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info("Created consumer group %s", CONSUMER_GROUP)
    except Exception:
        pass  # group already exists


async def _reclaim_stale(redis) -> None:
    """Re-queue messages that have been pending longer than VISIBILITY_S."""
    try:
        pending = await redis.xautoclaim(
            STREAM_KEY, CONSUMER_GROUP, CONSUMER_NAME,
            min_idle_time=VISIBILITY_S * 1000,
            start_id="0-0",
            count=10,
        )
        messages = pending[1] if isinstance(pending, (list, tuple)) and len(pending) > 1 else []
        if messages:
            logger.info("Reclaimed %d stale messages", len(messages))
    except Exception as exc:
        logger.debug("xautoclaim not available or failed: %s", exc)


async def consume() -> None:
    redis = await get_redis()
    await _ensure_consumer_group(redis)
    logger.info("Worker %s started, consuming from %s", CONSUMER_NAME, STREAM_KEY)

    while True:
        await _reclaim_stale(redis)

        messages = await redis.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            {STREAM_KEY: ">"},
            count=1,
            block=BLOCK_MS,
        )
        if not messages:
            continue

        for _stream, entries in messages:
            for msg_id, fields in entries:
                # Redis returns bytes when decode_responses=False, str when True
                job = {
                    k if isinstance(k, str) else k.decode(): v if isinstance(v, str) else v.decode()
                    for k, v in fields.items()
                }
                logger.info("Processing job %s for source %s", msg_id, job.get("source_id"))
                try:
                    async with AsyncSessionLocal() as db:
                        await run_ingestion_pipeline(db, job)
                    await redis.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                    logger.info("Completed job %s", msg_id)
                except Exception:
                    logger.exception("Job %s failed — will be reclaimed after %ds", msg_id, VISIBILITY_S)
                    # Do NOT ack — message stays pending and will be reclaimed


def main() -> None:
    loop = asyncio.new_event_loop()

    def _shutdown(sig, frame):
        logger.info("Received %s — shutting down", sig)
        loop.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(consume())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
