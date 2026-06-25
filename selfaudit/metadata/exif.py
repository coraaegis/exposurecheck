"""Minimal, dependency-free EXIF reader for privacy-relevant tags.

A leak audit only needs a handful of EXIF tags: GPS coordinates, capture time,
and camera make/model. Rather than pull a third-party image library into the
trusted base of a privacy tool, this parses the JPEG/Exif structure with the
standard library only. JPEG (JFIF/Exif) is supported in v1; HEIC and PNG are
TODO (X media is overwhelmingly JPEG).

Everything is wrapped defensively: a malformed file yields ``None`` or a partial
``ExifData``, never an exception that aborts an audit.
"""

from __future__ import annotations

import struct
from typing import Optional

from ..models import ExifData

# IFD0 / Exif tag ids
_TAG_MAKE = 0x010F
_TAG_MODEL = 0x0110
_TAG_DATETIME = 0x0132
_TAG_EXIF_IFD = 0x8769
_TAG_GPS_IFD = 0x8825
_TAG_DATETIME_ORIGINAL = 0x9003
# GPS sub-IFD tags
_GPS_LAT_REF = 0x0001
_GPS_LAT = 0x0002
_GPS_LON_REF = 0x0003
_GPS_LON = 0x0004

# TIFF field type -> byte size
_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}


def read_exif(path: str) -> Optional[ExifData]:
    """Read EXIF from a JPEG file path. Returns None if absent/unreadable."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    return read_exif_bytes(data)


def read_exif_bytes(data: bytes) -> Optional[ExifData]:
    """Read EXIF from raw JPEG bytes (used when reading media out of a .zip)."""
    tiff = _extract_tiff_from_jpeg(data)
    if tiff is None:
        return None
    try:
        exif = _parse_tiff(tiff)
    except Exception:
        return None
    # Treat an all-empty result as "no EXIF".
    if exif.gps_lat is None and exif.datetime_original is None and exif.make is None and exif.model is None:
        return None
    return exif


# --------------------------------------------------------------------------- #
#  JPEG segment scan -> raw TIFF block
# --------------------------------------------------------------------------- #

def _extract_tiff_from_jpeg(data: bytes) -> Optional[bytes]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":  # SOI
        return None
    i, n = 2, len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            i += 2  # markers without a length field
            continue
        if marker == 0xDA:  # start of scan; pixel data follows
            break
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        seg_start, seg_end = i + 4, i + 2 + seg_len
        if marker == 0xE1:  # APP1
            payload = data[seg_start:seg_end]
            if payload[:6] == b"Exif\x00\x00":
                return payload[6:]
        i = seg_end
    return None


# --------------------------------------------------------------------------- #
#  TIFF / IFD walk
# --------------------------------------------------------------------------- #

def _parse_tiff(tiff: bytes) -> ExifData:
    bo = tiff[:2]
    if bo == b"II":
        e = "<"
    elif bo == b"MM":
        e = ">"
    else:
        raise ValueError("bad TIFF byte order")
    if struct.unpack(e + "H", tiff[2:4])[0] != 0x002A:
        raise ValueError("bad TIFF magic")
    ifd0_off = struct.unpack(e + "I", tiff[4:8])[0]

    out = ExifData()
    ifd0 = _read_ifd(tiff, ifd0_off, e)

    if _TAG_MAKE in ifd0:
        out.make = _as_str(_value(tiff, ifd0[_TAG_MAKE], e))
    if _TAG_MODEL in ifd0:
        out.model = _as_str(_value(tiff, ifd0[_TAG_MODEL], e))
    if _TAG_DATETIME in ifd0:
        out.datetime_original = _as_str(_value(tiff, ifd0[_TAG_DATETIME], e))

    if _TAG_EXIF_IFD in ifd0:
        off = _scalar(_value(tiff, ifd0[_TAG_EXIF_IFD], e))
        if off:
            exif_ifd = _read_ifd(tiff, off, e)
            if _TAG_DATETIME_ORIGINAL in exif_ifd:
                out.datetime_original = _as_str(_value(tiff, exif_ifd[_TAG_DATETIME_ORIGINAL], e)) or out.datetime_original

    if _TAG_GPS_IFD in ifd0:
        off = _scalar(_value(tiff, ifd0[_TAG_GPS_IFD], e))
        if off:
            gps = _read_ifd(tiff, off, e)
            out.gps_lat = _gps_coord(tiff, gps, _GPS_LAT, _GPS_LAT_REF, e, ("S",))
            out.gps_lon = _gps_coord(tiff, gps, _GPS_LON, _GPS_LON_REF, e, ("W",))
    return out


def _read_ifd(tiff: bytes, offset: int, e: str) -> dict:
    entries: dict = {}
    if offset + 2 > len(tiff):
        return entries
    count = struct.unpack(e + "H", tiff[offset:offset + 2])[0]
    base = offset + 2
    for k in range(count):
        p = base + k * 12
        if p + 12 > len(tiff):
            break
        tag, typ, cnt = struct.unpack(e + "HHI", tiff[p:p + 8])
        entries[tag] = (typ, cnt, tiff[p + 8:p + 12])
    return entries


def _value(tiff: bytes, entry: tuple, e: str):
    typ, cnt, valfield = entry
    size = _TYPE_SIZES.get(typ, 1)
    total = size * cnt
    if total <= 4:
        raw = valfield[:total]
    else:
        off = struct.unpack(e + "I", valfield)[0]
        raw = tiff[off:off + total]
    return _decode(raw, typ, cnt, e)


def _decode(raw: bytes, typ: int, cnt: int, e: str):
    if typ == 2:  # ASCII
        return raw.split(b"\x00", 1)[0].decode("utf-8", "replace")
    if typ == 3:  # SHORT
        return list(struct.unpack(e + "H" * cnt, raw[:2 * cnt]))
    if typ == 4:  # LONG
        return list(struct.unpack(e + "I" * cnt, raw[:4 * cnt]))
    if typ == 9:  # SLONG
        return list(struct.unpack(e + "i" * cnt, raw[:4 * cnt]))
    if typ == 5:  # RATIONAL
        vals = struct.unpack(e + "I" * (2 * cnt), raw[:8 * cnt])
        return [(vals[2 * k], vals[2 * k + 1]) for k in range(cnt)]
    if typ == 10:  # SRATIONAL
        vals = struct.unpack(e + "i" * (2 * cnt), raw[:8 * cnt])
        return [(vals[2 * k], vals[2 * k + 1]) for k in range(cnt)]
    return list(raw)


def _as_str(v) -> Optional[str]:
    if isinstance(v, str):
        return v.strip() or None
    return None


def _scalar(v):
    if isinstance(v, list) and v:
        return v[0]
    return v


def _gps_coord(tiff, gps, tag, ref_tag, e, negative_refs) -> Optional[float]:
    if tag not in gps:
        return None
    dms = _value(tiff, gps[tag], e)
    if not isinstance(dms, list) or len(dms) < 3:
        return None

    def r(x):
        num, den = x
        return num / den if den else 0.0

    try:
        deg = r(dms[0]) + r(dms[1]) / 60.0 + r(dms[2]) / 3600.0
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    ref = _as_str(_value(tiff, gps[ref_tag], e)) if ref_tag in gps else None
    if ref and ref.upper() in negative_refs:
        deg = -deg
    return round(deg, 6)
