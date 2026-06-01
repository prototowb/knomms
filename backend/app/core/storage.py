"""MinIO object storage client — lazy init, used by pipeline + fork service."""

from miniopy_async import Minio  # type: ignore[import-untyped]

from app.core.config import settings

_client: Minio | None = None


def get_storage() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
    return _client


async def read_object(bucket: str, key: str) -> bytes:
    """Read an object from MinIO and return its bytes."""
    client = get_storage()
    response = await client.get_object(bucket, key)
    try:
        return await response.read()
    finally:
        await response.close()
        await response.release()
