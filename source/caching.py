"""Caching module."""

from pathlib import Path
import hashlib
import os
import sys

import polars as pl

APP_NAME = "microtonal_view"


def get_cache_directory() -> Path:
    """Get the system's cache directory for the application based on the OS."""
    home = Path.home()
    if os.name == "nt":  # Windows
        cache_dir = home / "AppData" / "Local" / APP_NAME / "Cache"
    elif os.name == "posix":
        if sys.platform == "darwin":  # macOS
            cache_dir = home / "Library" / "Caches" / APP_NAME
        else:  # Linux and other Unix-like OS
            cache_dir = home / ".cache" / APP_NAME
    else:
        raise RuntimeError("Unsupported operating system")

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def hash_file(file_path: Path) -> str:
    """Generate a SHA-256 hash of the file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


def save_to_cache(wav_hash: str, pitch_data: pl.DataFrame):
    """Save the Polars DataFrame to a cache file in the system's cache directory."""
    cache_dir = get_cache_directory()
    cache_file_path = cache_dir / f"{wav_hash}.parquet"
    pitch_data.write_parquet(cache_file_path)


def load_from_cache(wav_hash: str) -> pl.DataFrame | None:
    """Load the Polars DataFrame from a cache file if it exists."""
    cache_dir = get_cache_directory()
    cache_file_path = cache_dir / f"{wav_hash}.parquet"
    if cache_file_path.exists():
        return pl.read_parquet(cache_file_path)
    return None
