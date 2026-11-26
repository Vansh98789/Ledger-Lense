import os
from pathlib import Path
from typing import Optional

import boto3

LOCAL_UPLOAD_ROOT = Path(__file__).resolve().parents[1] / "data" / "uploads"

_s3_client = None


def _use_r2() -> bool:
    return bool(
        os.getenv("R2_ENDPOINT_URL")
        and os.getenv("R2_ACCESS_KEY_ID")
        and os.getenv("R2_SECRET_ACCESS_KEY")
        and os.getenv("R2_BUCKET_NAME")
    )


def _get_r2_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name="auto",
        )
    return _s3_client


def save_pdf(pdf_bytes: bytes, storage_key: str) -> str:
    """Save PDF bytes to Cloudflare R2 (if configured) or local disk."""
    if _use_r2():
        bucket = os.getenv("R2_BUCKET_NAME")
        _get_r2_client().put_object(
            Bucket=bucket,
            Key=storage_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        return storage_key

    target = LOCAL_UPLOAD_ROOT / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pdf_bytes)
    return storage_key


def load_pdf(storage_key: str) -> Optional[bytes]:
    """Load PDF bytes from Cloudflare R2 or local disk."""
    if _use_r2():
        bucket = os.getenv("R2_BUCKET_NAME")
        obj = _get_r2_client().get_object(Bucket=bucket, Key=storage_key)
        return obj["Body"].read()

    target = LOCAL_UPLOAD_ROOT / storage_key
    if not target.exists():
        return None
    return target.read_bytes()
