"""Deterministic metadata extraction (EXIF, etc.)."""
from .exif import read_exif, read_exif_bytes

__all__ = ["read_exif", "read_exif_bytes"]
