"""MinIO object storage client — lazy init, used by pipeline + ingestion services."""

from io import BytesIO

from miniopy_async import Minio  # type: ignore[import-untyped]

from app.core.config import settings

_client: Minio | None = None


def _endpoint_without_scheme(url: str) -> str:
    # miniopy-async prepends http:// or https:// itself based on the `secure`
    # param — passing a URL with a scheme results in http://http://... and fails.
    for scheme in ("https://", "http://"):
        if url.startswith(scheme):
            return url[len(scheme):]
    return url


def get_storage() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            _endpoint_without_scheme(settings.minio_endpoint),
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_endpoint.startswith("https://"),
        )
    return _client


async def ensure_bucket(bucket: str) -> None:
    """Create the bucket if it doesn't exist. Called once at app startup."""
    client = get_storage()
    if not await client.bucket_exists(bucket):
        await client.make_bucket(bucket)


async def write_object(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Write bytes to MinIO. Raises on failure."""
    client = get_storage()
    await client.put_object(bucket, key, BytesIO(data), length=len(data), content_type=content_type)


async def read_object(bucket: str, key: str) -> bytes:
    """Read an object from MinIO and return its bytes."""
    client = get_storage()
    response = await client.get_object(bucket, key)
    try:
        return await response.read()
    finally:
        await response.close()
        await response.release()
