"""
backup.py — automated PostgreSQL backup via pg_dump.

Creates a compressed .sql.gz dump and optionally uploads it to an S3-compatible
bucket (Backblaze B2, AWS S3, Cloudflare R2, etc.).

Run manually:
    python backup.py

Schedule on Render:
    Use a Render Cron Job service pointing to this file, e.g.:
    python backup.py --upload

Environment variables required:
    DATABASE_URL          — your existing Postgres URL
    BACKUP_DIR            — local directory for dumps (default: ./backups)
    BACKUP_RETAIN_DAYS    — how many local dumps to keep (default: 7)

For S3 upload (optional — set all 4 to enable):
    BACKUP_S3_BUCKET      — e.g. "lbca-backups"
    BACKUP_S3_ENDPOINT    — e.g. "https://s3.us-west-002.backblazeb2.com"
    BACKUP_S3_KEY_ID      — your access key ID
    BACKUP_S3_SECRET      — your secret access key
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

from logger import get_logger

logger = get_logger("backup")


# ── Config from environment ──────────────────────────────────────────────────

DATABASE_URL       = os.getenv("DATABASE_URL", "")
BACKUP_DIR         = Path(os.getenv("BACKUP_DIR", "./backups"))
BACKUP_RETAIN_DAYS = int(os.getenv("BACKUP_RETAIN_DAYS", "7"))
S3_BUCKET    = os.getenv("BACKUP_S3_BUCKET",   "")
S3_ENDPOINT  = os.getenv("BACKUP_S3_ENDPOINT", "")
S3_KEY_ID    = os.getenv("BACKUP_S3_KEY_ID",   "")
S3_SECRET    = os.getenv("BACKUP_S3_SECRET",   "")

S3_ENABLED = all([S3_BUCKET, S3_ENDPOINT, S3_KEY_ID, S3_SECRET])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_db_url(url: str) -> dict:
    """Break DATABASE_URL into connection parts for pg_dump."""
    u = urlparse(url.replace("postgres://", "postgresql://"))
    return {
        "host":     u.hostname or "localhost",
        "port":     str(u.port or 5432),
        "dbname":   u.path.lstrip("/"),
        "user":     u.username or "",
        "password": u.password or "",
    }


def _dump(parts: dict, dest: Path) -> None:
    """Run pg_dump and gzip the output."""
    env = os.environ.copy()
    env["PGPASSWORD"] = parts["password"]

    cmd = [
        "pg_dump",
        "-h", parts["host"],
        "-p", parts["port"],
        "-U", parts["user"],
        "-d", parts["dbname"],
        "--no-password",
        "--format=plain",
        "--no-owner",
        "--no-privileges",
    ]

    logger.info("Starting pg_dump", extra={"db": parts["dbname"], "host": parts["host"]})
    result = subprocess.run(cmd, capture_output=True, env=env, timeout=300)

    if result.returncode != 0:
        logger.error("pg_dump failed", extra={"stderr": result.stderr.decode()})
        raise RuntimeError(f"pg_dump exit code {result.returncode}")

    with gzip.open(dest, "wb") as f:
        f.write(result.stdout)

    size_kb = dest.stat().st_size // 1024
    logger.info("Dump written", extra={"file": str(dest), "size_kb": size_kb})


def _upload_s3(local_path: Path) -> None:
    """Upload the dump to an S3-compatible bucket using boto3."""
    try:
        import boto3
        from botocore.client import Config
    except ImportError:
        logger.warning("boto3 not installed — skipping S3 upload. Run: pip install boto3")
        return

    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_KEY_ID,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
    )

    key = f"backups/{local_path.name}"
    s3.upload_file(str(local_path), S3_BUCKET, key)
    logger.info("Uploaded to S3", extra={"bucket": S3_BUCKET, "key": key})


def _prune_old_backups() -> None:
    """Delete local dumps older than BACKUP_RETAIN_DAYS."""
    cutoff = time.time() - BACKUP_RETAIN_DAYS * 86400
    for f in BACKUP_DIR.glob("*.sql.gz"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            logger.info("Pruned old backup", extra={"file": str(f)})


# ── Main ─────────────────────────────────────────────────────────────────────

def run_backup(upload: bool = False) -> Path:
    if not DATABASE_URL:
        logger.error("DATABASE_URL is not set")
        sys.exit(1)

    if not shutil.which("pg_dump"):
        logger.error("pg_dump not found in PATH. Install postgresql-client.")
        sys.exit(1)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    ts   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"lbca_{ts}.sql.gz"

    parts = _parse_db_url(DATABASE_URL)
    _dump(parts, dest)
    _prune_old_backups()

    if upload and S3_ENABLED:
        _upload_s3(dest)
    elif upload and not S3_ENABLED:
        logger.warning("S3 upload requested but S3 env vars not set — skipping")

    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LBCA database backup")
    parser.add_argument("--upload", action="store_true", help="Upload dump to S3 after creating it")
    args = parser.parse_args()
    path = run_backup(upload=args.upload)
    print(f"Backup complete: {path}")
