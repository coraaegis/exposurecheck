"""Uniform read access to an export, whether it is an unzipped directory or a .zip.

Both parsers go through this so they don't care which form the user points at,
and so image bytes can be pulled out of a .zip for EXIF without extracting it.
"""

from __future__ import annotations

import os
import zipfile
from typing import Optional


class ExportSource:
    def __init__(self, path: str):
        self.path = path
        self._zip: Optional[zipfile.ZipFile] = None
        self._names: list[str] = []
        if os.path.isfile(path) and path.lower().endswith(".zip"):
            try:
                self._zip = zipfile.ZipFile(path)
                self._names = self._zip.namelist()
            except (zipfile.BadZipFile, OSError) as e:
                raise ValueError(f"not a readable .zip: {path} ({e})") from e
        elif os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for fn in files:
                    rel = os.path.relpath(os.path.join(root, fn), path)
                    self._names.append(rel.replace("\\", "/"))
        else:
            raise FileNotFoundError(f"not a directory or .zip: {path}")

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def __enter__(self) -> "ExportSource":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- lookups ----------------------------------------------------------- #

    def find(self, *basenames: str) -> Optional[str]:
        """Return the first stored path whose basename matches (case-insensitive)."""
        wanted = {b.lower() for b in basenames}
        for name in self._names:
            if os.path.basename(name).lower() in wanted:
                return name
        return None

    def list_dir(self, *dir_basenames: str) -> list[str]:
        """List stored files living under any directory with one of these basenames."""
        wanted = {d.lower().strip("/") for d in dir_basenames}
        out = []
        for name in self._names:
            parts = name.split("/")
            if any(p.lower() in wanted for p in parts[:-1]):
                out.append(name)
        return out

    def read_bytes(self, relpath: str) -> Optional[bytes]:
        try:
            if self._zip is not None:
                return self._zip.read(relpath)
            with open(os.path.join(self.path, relpath), "rb") as f:
                return f.read()
        except (KeyError, OSError):
            return None

    def read_text(self, *basenames: str, encoding: str = "utf-8") -> Optional[str]:
        rel = self.find(*basenames)
        if rel is None:
            return None
        data = self.read_bytes(rel)
        if data is None:
            return None
        return data.decode(encoding, "replace")
