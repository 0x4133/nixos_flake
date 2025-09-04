#!/usr/bin/env python3
# Decode ROBOTIS HLDS (HLS-LFCD2 / LDS-01) frames from an Arduino UNO R4 bridge.
# - Opens /dev/ttyACM0 @ 230400 8N1
# - Sends 'b' to begin streaming
# - Decodes 42-byte frames -> 6 (angle,distance,intensity) readings
# - Prints CSV: angle,distance_mm,intensity  (one line per angle update)

import os
import sys
import time
import serial
from collections import defaultdict

PORT = "/dev/ttyACM0"
BAUD = 115200
START_CMD = b"b"   # begin streaming
PAUSE_CMD = b"e"   # pause streaming

# Basic plausibility checks from LDS docs:
ANGLE_INDEX_MIN = 0xA0  # 160
ANGLE_INDEX_MAX = 0xDB  # 219
FRAME_LEN = 42
MEAS_PER_FRAME = 6

def open_port(port: str, baud: int) -> serial.Serial:
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=0.2)
        return ser
    except Exception as e:
        print(f"Error: cannot open {port}: {e}")
        sys.exit(1)

def is_plausible_frame(buf: bytes) -> bool:
    if len(buf) != FRAME_LEN:
        return False
    idx = buf[1]
    if not (ANGLE_INDEX_MIN <= idx <= ANGLE_INDEX_MAX):
        return False
    # Many devices mirror the last 2 bytes for a quick validity check
    if buf[-1] != buf[-2]:
        return False
    return True

def decode_frame(buf: bytes):
    """
    Returns:
      base_angle: int (0..354 step 6)
      rpm_raw: int (little-endian, bytes[2:4])  # raw speed value from device
      samples: list of (angle, distance_mm, intensity)
    """
    idx = buf[1]
    base_angle = (idx - 160) * 6  # angle index (A0..DB) → 0..60 blocks → degrees
    # RPM value (per spec table: low at [2], high at [3])
    rpm_raw = buf[2] | (buf[3] << 8)

    samples = []
    # Each of the 6 measurements takes 6 bytes; distance lo/hi then intensity
    # Offsets for k in 0..5: base = 6*(k+1)
    for k in range(MEAS_PER_FRAME):
        base = 6 * (k + 1)
        dist_lo = buf[base + 0]
        dist_hi = buf[base + 1]
        intensity = buf[base + 2]
        distance = (dist_hi << 8) | dist_lo
        angle = (base_angle + k) % 360
        samples.append((angle, distance, intensity))
    return base_angle, rpm_raw, samples

def resync(ser: serial.Serial):
    """Read and slide until a plausible 42-byte frame is found."""
    # read a larger chunk then slide a 42-byte window
    chunk = ser.read(200)
    if len(chunk) < FRAME_LEN:
        return None
    for start in range(0, len(chunk) - FRAME_LEN + 1):
        frame = chunk[start:start+FRAME_LEN]
        if is_plausible_frame(frame):
            return frame
    retu
