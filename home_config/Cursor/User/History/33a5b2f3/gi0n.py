#!/usr/bin/env python3
"""
Capture LDS-style LiDAR from /dev/ttyUSB0 and write a LAS 1.2 point cloud
WITHOUT NumPy or laspy (pure Python, stdlib only).

- Tries 230400, then 115200 baud.
- Packet: 42 bytes:
  [0]=0xFA sync,
  [1]=0xA0..0xDB angle index (index = byte-0xA0),
  [2..3]=RPM little-endian,
  6 blocks for offsets 0..5, each 6 bytes: [I_lo,I_hi, D_lo,D_hi, R_lo,R_hi]
  [40..41]=checksum (sum of first 40 bytes & 0xFFFF)
- Output: LAS 1.2, Point Data Format 0 (20 bytes/point), millimeter scale.

Usage:
  python3 lidar_to_las_pure.py --dev /dev/ttyUSB0 --duration 10 --out scan.las
  python3 lidar_to_las_pure.py --dev /dev/ttyUSB0 --max-points 50000 --out scan.las
"""

import argparse
import math
import struct
import sys
import time
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

import serial

SYNC = 0xFA
ANGLE_INDEX_MIN = 0xA0
ANGLE_INDEX_MAX = 0xDB  # inclusive
PACKET_LEN = 42

# LAS constants (v1.2)
LAS_VERSION_MAJOR = 1
LAS_VERSION_MINOR = 2
LAS_HEADER_SIZE = 227
LAS_POINT_FORMAT = 0   # format 0 -> 20 bytes per point
LAS_POINT_RECORD_LEN = 20
LAS_VLR_COUNT = 0
LAS_SYSTEM_ID = "PY-LiDAR"
LAS_SOFTWARE_ID = "PurePy LAS 1.2"

@dataclass
class LidarPoint:
    angle_deg: int
    distance_mm: int
    intensity: int

@dataclass
class LidarPacket:
    angle_index: int
    rpm: int
    checksum_ok: bool
    points: List[LidarPoint]

def u16(lo: int, hi: int) -> int:
    return (hi << 8) | lo

def calc_checksum(payload40: bytes) -> int:
    return sum(payload40) & 0xFFFF

def parse_packet(buf: bytes) -> Optional[LidarPacket]:
    if len(buf) != PACKET_LEN or buf[0] != SYNC:
        return None
    idx_byte = buf[1]
    if not (ANGLE_INDEX_MIN <= idx_byte <= ANGLE_INDEX_MAX):
        return None
    angle_index = idx_byte - ANGLE_INDEX_MIN
    rpm = u16(buf[2], buf[3])

    expected = u16(buf[40], buf[41])
    computed = calc_checksum(buf[:40])
    checksum_ok = (expected == computed)

    points: List[LidarPoint] = []
    p = 4
    for offset in range(6):
        intensity = u16(buf[p + 0], buf[p + 1])
        dist_mm   = u16(buf[p + 2], buf[p + 3])
        p += 6  # skip 2 reserved bytes too
        angle = (angle_index * 6 + offset) % 360
        points.append(LidarPoint(angle, dist_mm, intensity))

    return LidarPacket(angle_index, rpm, checksum_ok, points)

def read_exact(ser: serial.Serial, n: int, timeout_s: float = 1.0) -> Optional[bytes]:
    data = bytearray()
    end = time.time() + timeout_s
    while len(data) < n:
        if time.time() > end:
            return None
        chunk = ser.read(n - len(data))
        if not chunk:
            time.sleep(0.001)
            continue
        data.extend(chunk)
    return bytes(data)

def packet_stream(ser: serial.Serial) -> Iterator[bytes]:
    while True:
        b = ser.read(1)
        if not b:
            continue
        if b[0] != SYNC:
            continue
        rest = read_exact(ser, PACKET_LEN - 1, timeout_s=0.2)
        if rest is None:
            continue
        yield bytes([SYNC]) + rest

def try_open(dev: str, baud: int, timeout: float = 0.2) -> Optional[serial.Serial]:
    try:
        ser = serial.Serial(
            port=dev,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser
    except Exception as e:
        sys.stderr.write(f"[!] Could not open {dev} @ {baud}: {e}\n")
        return None

def detect_baud(dev: str, candidates=(230400, 115200), sample_packets=8) -> Tuple[serial.Serial, int]:
    for baud in candidates:
        ser = try_open(dev, baud)
        if ser is None:
            continue
        good = 0
        start = time.time()
        for raw in packet_stream(ser):
            pkt = parse_packet(raw)
            if pkt:
                good += 1
            if good >= sample_packets:
                sys.stderr.write(f"[+] Locked on {dev} @ {baud}\n")
                return ser, baud
            if time.time() - start > 2.0:
                break
        ser.close()
    raise RuntimeError("Failed to detect a working baud.")

def polar_to_cartesian(angle_deg: int, dist_mm: int) -> Tuple[float, float, float]:
    r_m = dist_mm / 1000.0
    theta = math.radians(angle_deg)
    return r_m * math.cos(theta), r_m * math.sin(theta), 0.0

def collect_points(dev: str, duration_s: float, max_points: int = 0) -> List[Tuple[float, float, float, int]]:
    ser, _ = detect_baud(dev, candidates=(230400, 115200))
    pts: List[Tuple[float, float, float, int]] = []
    start = time.time()
    pkt_count = 0
    try:
        for raw in packet_stream(ser):
            pkt = parse_packet(raw)
            if not pkt:
                continue
            pkt_count += 1
            for pt in pkt.points:
                x, y, z = polar_to_cartesian(pt.angle_deg, pt.distance_mm)
                pts.append((x, y, z, pt.intensity))
                if max_points and len(pts) >= max_points:
                    raise KeyboardInterrupt
            if duration_s > 0 and (time.time() - start) >= duration_s:
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            ser.close()
        except Exception:
            pass
    sys.stderr.write(f"[i] Collected {len(pts)} points from {pkt_count} packets\n")
    return pts

# ---- LAS writing (pure Python) ----

def write_las_v12_format0(out_path: str, points_xyz_i: List[Tuple[float, float, float, int]],
                          scale=(0.001, 0.001, 0.001), offset=(0.0, 0.0, 0.0)) -> None:
    """
    Write LAS 1.2 header and Format 0 point records.
    Format 0 layout (little-endian, 20 bytes):
      int32 X, int32 Y, int32 Z, uint16 intensity,
      uint8 returnFlags, uint8 classification, int8 scanAngleRank,
      uint8 userData, uint16 pointSourceId
    """
    sx, sy, sz = scale
    ox, oy, oz = offset

    # Convert to scaled ints and compute bounds
    Xs: List[int] = []
    Ys: List[int] = []
    Zs: List[int] = []
    Is: List[int] = []
    for x, y, z, inten in points_xyz_i:
        Xs.append(int(round((x - ox) / sx)))
        Ys.append(int(round((y - oy) / sy)))
        Zs.append(int(round((z - oz) / sz)))
        Is.append(int(max(0, min(65535, inten))))

    if not Xs:
        raise ValueError("No points to write.")

    # Compute min/max in double-precision space (LAS stores mins/maxs as float64)
    min_x = min(Xs) * sx + ox
    min_y = min(Ys) * sy + oy
    min_z = min(Zs) * sz + oz
    max_x = max(Xs) * sx + ox
    max_y = max(Ys) * sy + oy
    max_z = max(Zs) * sz + oz

    num_points = len(Xs)
    by_return = [0, 0, 0, 0, 0]  # we don't track returns; all go into first bin
    by_return[0] = num_points

    # File header
    with open(out_path, "wb") as f:
        # File Signature 'LASF'
        f.write(b'LASF')

        # File Source ID (2), Global Encoding (2)
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))

        # Project ID GUID data (16 bytes) -> zeros
        f.write(b'\x00' * 16)

        # Version Major (1), Minor (1)
        f.write(struct.pack('<BB', LAS_VERSION_MAJOR, LAS_VERSION_MINOR))

        # System Identifier (32), Generating Software (32)
        sys_id = LAS_SYSTEM_ID.encode('ascii')[:32]
        gen_sw = LAS_SOFTWARE_ID.encode('ascii')[:32]
        f.write(sys_id + b'\x00' * (32 - len(sys_id)))
        f.write(gen_sw + b'\x00' * (32 - len(gen_sw)))

        # File Creation Day/Year — use current UTC day-of-year and year
        t = time.gmtime()
        day_of_year = int(time.strftime("%j", t))
        year = t.tm_year
        f.write(struct.pack('<HH', day_of_year, year))

        # Header Size, Offset to point data
        offset_to_points = LAS_HEADER_SIZE  # no VLRs
        f.write(struct.pack('<H', LAS_HEADER_SIZE))
        f.write(struct.pack('<I', offset_to_points))

        # Number of Variable Length Records
        f.write(struct.pack('<I', LAS_VLR_COUNT))

        # Point Data Format (1), Point Data Record Length (2)
        f.write(struct.pack('<B', LAS_POINT_FORMAT))
        f.write(struct.pack('<H', LAS_POINT_RECORD_LEN))

        # Legacy: Number of point records (4) and by return (5 * 4)
        f.write(struct.pack('<I', num_points))
        for n in by_return:
            f.write(struct.pack('<I', n))

        # Scale factors (X,Y,Z) as float64
        f.write(struct.pack('<ddd', sx, sy, sz))
        # Offsets (X,Y,Z) as float64
        f.write(struct.pack('<ddd', ox, oy, oz))
        # Max/Min (X,Y,Z) as float64 (note order: max, min)
        f.write(struct.pack('<ddd', max_x, max_y, max_z))
        f.write(struct.pack('<ddd', min_x, min_y, min_z))

        # --- Points ---
        # Default filler fields for format 0:
        returnFlags = 0  # (return number 0, number of returns 0, edge bits 0)
        classification = 1  # "unclassified"
        scanAngleRank = 0
        userData = 0
        pointSourceId = 0

        # Pack each point
        for X, Y, Z, I in zip(Xs, Ys, Zs, Is):
            f.write(struct.pack('<iiiHBBbBH',
                                X, Y, Z,
                                I,
                                returnFlags,
                                classification,
                                scanAngleRank,
                                userData,
                                pointSourceId))

    sys.stderr.write(f"[+] Wrote LAS 1.2 (Format 0) to {out_path} with {num_points} points\n")

def main():
    ap = argparse.ArgumentParser(description="Capture LiDAR to LAS 1.2 (pure Python, no NumPy).")
    ap.add_argument("--dev", default="/dev/ttyUSB0", help="Serial device (default: /dev/ttyUSB0)")
    ap.add_argument("--duration", type=float, default=10.0, help="Seconds to capture (0 = until Ctrl-C)")
    ap.add_argument("--max-points", type=int, default=0, help="Stop after N points (0 = unlimited)")
    ap.add_argument("--out", required=True, help="Output .las path")
    ap.add_argument("--scale-mm", type=float, default=1.0, help="Coordinate scale in millimeters (default 1.0 => 0.001 m)")
    args = ap.parse_args()

    # Scale: user passes in millimeters; convert to meters
    s = args.scale_mm / 1000.0
    scale = (s, s, s)
    offset = (0.0, 0.0, 0.0)

    pts = collect_points(args.dev, duration_s=args.duration, max_points=args.max_points)
    if not pts:
        sys.stderr.write("[!] No points captured\n")
        sys.exit(1)

    write_las_v12_format0(args.out, pts, scale=scale, offset=offset)

if __name__ == "__main__":
    main()
