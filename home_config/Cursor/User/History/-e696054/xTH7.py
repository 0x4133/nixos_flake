#!/usr/bin/env python3
"""
LDS-style LiDAR frame reader for /dev/ttyUSB0.

Frame (42 bytes total):
  0   : 0xFA                           -> sync
  1   : 0xA0..0xDB                     -> Angle Index (0..60) = byte - 0xA0
  2-3 : RPM (little-endian, uint16)
  Repeated for offsets 0..5 (6 points):
    intensity_lo, intensity_hi, dist_lo, dist_hi, rsv_lo, rsv_hi
  40-41 : checksum (little-endian, uint16) == sum(bytes[0:40]) & 0xFFFF

Each packet yields 6 points:
  angle_deg = (angle_index * 6 + offset) % 360
  distance_mm = uint16
  intensity   = uint16
"""

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

import serial

SYNC = 0xFA
ANGLE_INDEX_MIN = 0xA0
ANGLE_INDEX_MAX = 0xDB  # inclusive
PACKET_LEN = 42

@dataclass
class LidarPoint:
    angle_deg: int         # 0..359
    distance_mm: int       # 0..65535
    intensity: int         # 0..65535

@dataclass
class LidarPacket:
    angle_index: int       # 0..60
    rpm: int               # raw rpm value (sensor-specific scaling)
    checksum_ok: bool
    points: List[LidarPoint]  # exactly 6

def u16(lo: int, hi: int) -> int:
    return (hi << 8) | lo

def calc_checksum(payload40: bytes) -> int:
    """Simple 16-bit sum over first 40 bytes (per many LDS variants)."""
    return sum(payload40) & 0xFFFF

def parse_packet(buf: bytes) -> Optional[LidarPacket]:
    if len(buf) != PACKET_LEN:
        return None
    if buf[0] != SYNC:
        return None
    idx_byte = buf[1]
    if not (ANGLE_INDEX_MIN <= idx_byte <= ANGLE_INDEX_MAX):
        return None

    angle_index = idx_byte - ANGLE_INDEX_MIN
    rpm = u16(buf[2], buf[3])

    # Verify checksum (non-fatal if it fails)
    expected = u16(buf[40], buf[41])
    computed = calc_checksum(buf[:40])
    checksum_ok = (expected == computed)

    # Offsets 0..5, each block = 6 bytes: I(2), D(2), R(2)
    points: List[LidarPoint] = []
    p = 4
    for offset in range(6):
        intensity = u16(buf[p + 0], buf[p + 1])
        dist_mm   = u16(buf[p + 2], buf[p + 3])
        # rsv_lo = buf[p + 4]; rsv_hi = buf[p + 5]  # currently unused
        p += 6
        angle = (angle_index * 6 + offset) % 360
        points.append(LidarPoint(angle, dist_mm, intensity))

    return LidarPacket(angle_index, rpm, checksum_ok, points)

def read_exact(ser: serial.Serial, n: int, timeout_s: float = 1.0) -> Optional[bytes]:
    """Read exactly n bytes or None on timeout."""
    data = bytearray()
    end = time.time() + timeout_s
    while len(data) < n:
        if time.time() > end:
            return None
        chunk = ser.read(n - len(data))
        if not chunk:
            # short sleep to avoid spin if no bytes available
            time.sleep(0.001)
            continue
        data.extend(chunk)
    return bytes(data)

def packet_stream(ser: serial.Serial) -> Iterator[bytes]:
    """Yield raw 42-byte frames aligned on SYNC."""
    buf = bytearray()
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
        # small purge
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser
    except Exception as e:
        sys.stderr.write(f"[!] Could not open {dev} @ {baud}: {e}\n")
        return None

def detect_baud(dev: str, candidates=(230400, 115200), sample_packets=10) -> Tuple[serial.Serial, int]:
    """Pick the first baud that yields plausible frames."""
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
    raise RuntimeError("Failed to detect a working baud (tried: %s)" % (candidates,))

def main():
    ap = argparse.ArgumentParser(description="Read LDS LiDAR frames and emit angle, distance, intensity.")
    ap.add_argument("--dev", default="/dev/ttyUSB0", help="Serial device (default: /dev/ttyUSB0)")
    ap.add_argument("--csv", default=None, help="Optional CSV output path")
    ap.add_argument("--max-packets", type=int, default=0, help="Stop after N packets (0 = run forever)")
    ap.add_argument("--print-rpm", action="store_true", help="Print RPM periodically")
    args = ap.parse_args()

    try:
        ser, baud = detect_baud(args.dev, candidates=(230400, 115200))
    except Exception as e:
        sys.stderr.write(f"[!] {e}\n")
        sys.exit(1)

    csv_writer = None
    csv_file = None
    if args.csv:
        csv_file = open(args.csv, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["packet_index", "rpm_raw", "checksum_ok", "angle_deg", "distance_mm", "intensity"])

    pkt_count = 0
    last_rpm_print = 0.0

    try:
        for raw in packet_stream(ser):
            pkt = parse_packet(raw)
            if not pkt:
                continue

            pkt_count += 1
            if args.print_rpm and (time.time() - last_rpm_print) > 1.0:
                sys.stderr.write(f"[rpm] raw={pkt.rpm}  checksum={'ok' if pkt.checksum_ok else 'BAD'}\n")
                last_rpm_print = time.time()

            # Stream points
            for pt in pkt.points:
                line = f"{pt.angle_deg:3d},{pt.distance_mm:5d},{pt.intensity:5d}"
                print(line)
                if csv_writer:
                    csv_writer.writerow([pkt_count, pkt.rpm, int(pkt.checksum_ok), pt.angle_deg, pt.distance_mm, pt.intensity])

            if args.max-packets and pkt_count >= args.max_packets:
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            ser.close()
        except Exception:
            pass
        if csv_file:
            csv_file.close()

if __name__ == "__main__":
    main()
