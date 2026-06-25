"""Generate a tiny synthetic JPEG carrying EXIF GPS, for parser tests.

Builds the TIFF/IFD structure by hand (no image libs) so the fixture is fully
synthetic and reproducible. Encodes GPS 47deg36'0" N, 122deg19'12" W -> the
parser should recover (47.6, -122.32) and Make="Cam". Run from the repo root:

    python tests/_make_exif_fixture.py
"""

import os
import struct


def _entry(tag, typ, count, value4):
    assert len(value4) == 4
    return struct.pack("<HHI", tag, typ, count) + value4


def _inline(b):
    return (b + b"\x00\x00\x00\x00")[:4]


def _off(o):
    return struct.pack("<I", o)


def build_jpeg_with_gps() -> bytes:
    lat_data = b"".join(struct.pack("<II", n, d) for n, d in [(47, 1), (36, 1), (0, 1)])
    lon_data = b"".join(struct.pack("<II", n, d) for n, d in [(122, 1), (19, 1), (12, 1)])

    gps_ifd_off, lat_off, lon_off = 38, 92, 116

    gps_ifd = struct.pack("<H", 4)
    gps_ifd += _entry(0x0001, 2, 2, _inline(b"N\x00"))      # GPSLatitudeRef
    gps_ifd += _entry(0x0002, 5, 3, _off(lat_off))          # GPSLatitude
    gps_ifd += _entry(0x0003, 2, 2, _inline(b"W\x00"))      # GPSLongitudeRef
    gps_ifd += _entry(0x0004, 5, 3, _off(lon_off))          # GPSLongitude
    gps_ifd += struct.pack("<I", 0)

    ifd0 = struct.pack("<H", 2)
    ifd0 += _entry(0x010F, 2, 4, _inline(b"Cam\x00"))       # Make
    ifd0 += _entry(0x8825, 4, 1, _off(gps_ifd_off))         # GPSInfo IFD pointer
    ifd0 += struct.pack("<I", 0)

    tiff = b"II" + struct.pack("<H", 0x2A) + struct.pack("<I", 8)
    tiff += ifd0 + gps_ifd + lat_data + lon_data

    exif_payload = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(exif_payload) + 2) + exif_payload
    return b"\xff\xd8" + app1 + b"\xff\xd9"  # SOI + APP1 + EOI


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(
        here, "fixtures", "twitter_sample", "data", "tweets_media",
        "1500000000000000005-AbCd1234.jpg",
    )
    with open(out, "wb") as f:
        f.write(build_jpeg_with_gps())
    print("wrote", out, os.path.getsize(out), "bytes")
