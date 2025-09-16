#!/usr/bin/env python3
"""
Stream LDS-style LiDAR data from /dev/ttyUSB0 and write LAS/LAZ for QGIS.

- Tries 230400, then 115200
- Frame: 42 bytes (0xFA sync, 0xA0..0xDB angle index, 2B RPM, then 6 blocks of
  [Intensity(2), Distance_mm(2), Reserved(2)], and 2B checksum)
- Output: .laz if lazrs is present and outfile ends with .laz, else .las

Example:
  python3 lidar_to_las.py --dev /dev/ttyUSB0 --duration 10 --out scan.laz
"""

import argparse
import math
import sys
import time
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

import serial
import laspy

SYNC = 0xFA
ANGLE_INDEX_MIN = 0xA0
ANGLE_INDEX_MAX = 0xDB  # inclusive
PACKET_LEN = 42

@dataclass
class LidarPoint:
    angle_deg: int       # 0..359
    distance_mm: int     # 0..65535
    intensity: int       # 0..65535

@dataclass
class LidarPacket:
    angle_index: int     # 0..60
    rpm: int             # raw rpm value
    checksum_ok: bool
    points: List[LidarPoint]

def u16(lo: int, hi: int) -> int:
    return (hi << 8) | lo

def calc_checksum(payload40: bytes) -> int:
    # Simple 16-bit sum over first 40 bytes (common LDS variant)
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
        p += 6  # skip reserved two bytes as well
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
    """Returns (x, y, z) in meters, Z=0 for 2D scanner."""
    r_m = dist_mm / 1000.0
    theta = math.radians(angle_deg)
    x = r_m * math.cos(theta)
    y = r_m * math.sin(theta)
    z = 0.0
    return x, y, z

def collect_points(dev: str, duration_s: float, max_points: int = 0) -> Tuple[List[float], List[float], List[float], List[int]]:
    ser, _ = detect_baud(dev, candidates=(230400, 115200))
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    intens: List[int] = []

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
                xs.append(x); ys.append(y); zs.append(z); intens.append(pt.intensity)
                if max_points and len(xs) >= max_points:
                    raise KeyboardInterrupt  # quick exit to finalize
            if duration_s > 0 and (time.time() - start) >= duration_s:
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            ser.close()
        except Exception:
            pass
    sys.stderr.write(f"[i] Collected {len(xs)} points from {pkt_count} packets\n")
    return xs, ys, zs, intens

def write_las_or_laz(out_path: str, xs: List[float], ys: List[float], zs: List[float], intens: List[int]) -> None:
    # Create LAS 1.4 with point format 3 (has intensity; we won’t use RGB/time)
    las = laspy.create(file_version="1.4", point_format=3)

    # Set header scales/offsets for decent precision
    # (LAS stores scaled ints; choose small scales for good precision)
    las.header.scales = (0.001, 0.001, 0.001)   # millimeter resolution
    las.header.offsets = (0.0, 0.0, 0.0)

    # Assign coordinates (floats are scaled to ints internally)
    import numpy as np
    las.x = np.asarray(xs, dtype=np.float64)
    las.y = np.asarray(ys, dtype=np.float64)
    las.z = np.asarray(zs, dtype=np.float64)

    # Intensity must be uint16
    las.intensity = np.asarray(intens, dtype=np.uint16)

    # Try to write .laz if requested; otherwise writes .las
    try:
        las.write(out_path)
        sys.stderr.write(f"[+] Wrote {out_path}\n")
    except laspy.LaspyException as e:
        # If user requested .laz but no compressor is installed, suggest .las
        sys.stderr.write(f"[!] Failed writing {out_path}: {e}\n")
        if out_path.lower().endswith(".laz"):
            alt = out_path[:-4] + ".las"
            sys.stderr.write(f"[>] Retrying as {alt}\n")
            las.write(alt)
            sys.stderr.write(f"[+] Wrote {alt}\n")
        else:
            raise

def main():
    ap = argparse.ArgumentParser(description="Capture LiDAR to LAS/LAZ for QGIS.")
    ap.add_argument("--dev", default="/dev/ttyUSB0", help="Serial device (default: /dev/ttyUSB0)")
    ap.add_argument("--duration", type=float, default=10.0, help="Seconds to capture (0 = until Ctrl-C)")
    ap.add_argument("--max-points", type=int, default=0, help="Stop after N points (0 = unlimited)")
    ap.add_argument("--out", required=True, help="Output .las or .laz path")
    args = ap.parse_args()

    xs, ys, zs, intens = collect_points(args.dev, duration_s=args.duration, max_points=args.max_points)
    if not xs:
        sys.stderr.write("[!] No points captured. Is the sensor streaming?\n")
        sys.exit(1)

    write_las_or_laz(args.out, xs, ys, zs, intens)

if __name__ == "__main__":
    main()
