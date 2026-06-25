"""EXIF parser must not crash, hang, or over-allocate on adversarial JPEGs."""

import struct
import time

from exposurecheck.metadata.exif import read_exif_bytes


def _jpeg_with_app1(tiff: bytes) -> bytes:
    payload = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    return b"\xff\xd8" + app1 + b"\xff\xd9"


def test_giant_count_does_not_hang_or_oom():
    # one IFD0 entry, type SHORT (3), count = 0xFFFFFFFF, inline value field.
    # Pre-fix this builds a ~4-billion-element struct format -> multi-GB / many seconds.
    ifd = struct.pack("<H", 1)
    ifd += struct.pack("<HHI", 0x010F, 3, 0xFFFFFFFF) + b"\x00\x00\x00\x00"
    ifd += struct.pack("<I", 0)
    tiff = b"II" + struct.pack("<H", 0x2A) + struct.pack("<I", 8) + ifd

    t0 = time.time()
    result = read_exif_bytes(_jpeg_with_app1(tiff))  # must return quickly, no exception
    assert time.time() - t0 < 2.0
    assert result is None or result.gps_lat is None  # no valid data, but no crash


def test_truncated_and_garbage_inputs_return_none():
    assert read_exif_bytes(b"") is None
    assert read_exif_bytes(b"\xff\xd8") is None
    assert read_exif_bytes(b"\xff\xd8" + b"\x00" * 50) is None
    assert read_exif_bytes(_jpeg_with_app1(b"II")) is None  # truncated TIFF


def test_bad_gps_does_not_void_make():
    # valid Make in IFD0 + a GPS pointer to an out-of-range offset.
    ifd0 = struct.pack("<H", 2)
    ifd0 += struct.pack("<HHI", 0x010F, 2, 4) + b"Cam\x00"          # Make = "Cam"
    ifd0 += struct.pack("<HHI", 0x8825, 4, 1) + struct.pack("<I", 9999)  # GPS IFD off-range
    ifd0 += struct.pack("<I", 0)
    tiff = b"II" + struct.pack("<H", 0x2A) + struct.pack("<I", 8) + ifd0
    result = read_exif_bytes(_jpeg_with_app1(tiff))
    assert result is not None and result.make == "Cam"  # GPS failure didn't void IFD0
