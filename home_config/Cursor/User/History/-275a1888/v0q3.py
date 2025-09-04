#!/usr/bin/env python3
# Decode ROBOTIS HLDS (HLS-LFCD2 / LDS-01) frames and also log raw bytes to a file.

import os
import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200
START_CMD = b"b"
PAUSE_CMD = b"e"

FRAME_LEN = 42
ANGLE_INDEX_MIN = 0xA0
ANGLE_INDEX_MAX = 0xDB

def open_port(port, baud):
    try:
        return serial.Serial(port, baudrate=baud, timeout=0.2)
    except Exception as e:
        print(f"Error opening {port}: {e}")
        sys.exit(1)

def is_plausible_frame(buf: bytes) -> bool:
    if len(buf) != FRAME_LEN:
        return False
    idx = buf[1]
    if not (ANGLE_INDEX_MIN <= idx <= ANGLE_INDEX_MAX):
        return False
    if buf[-1] != buf[-2]:
        return False
    return True

def decode_frame(buf: bytes):
    idx = buf[1]
    base_angle = (idx - 160) * 6
    samples = []
    for k in range(6):
        base = 6 * (k + 1)
        dist = buf[base] | (buf[base+1] << 8)
        inten = buf[base+2]
        angle = (base_angle + k) % 360
        samples.append((angle, dist, inten))
    return samples

def main():
    if not os.path.exists(PORT):
        print(f"{PORT} not found")
        sys.exit(1)

    ser = open_port(PORT, BAUD)
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(START_CMD)

    with open("lidar_raw.txt", "w") as logfile:
        print("Logging raw frames to lidar_raw.txt ... Ctrl-C to stop")
        try:
            while True:
                frame = ser.read(FRAME_LEN)
                if len(frame) != FRAME_LEN or not is_plausible_frame(frame):
                    continue

                # 1) Write raw bytes to file in hex
                hexline = " ".join(f"{b:02X}" for b in frame)
                logfile.write(hexline + "\n")
                logfile.flush()

                # 2) Decode and print to console
                for angle, dist, inten in decode_frame(frame):
                    print(f"{angle},{dist},{inten}")

        except KeyboardInterrupt:
            pass
        finally:
            try:
                ser.write(PAUSE_CMD)
            except Exception:
                pass
            ser.close()
            print("\nStopped.")

if __name__ == "__main__":
    main()
