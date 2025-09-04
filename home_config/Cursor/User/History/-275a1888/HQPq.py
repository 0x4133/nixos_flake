#!/usr/bin/env python3
import serial, sys, math, time
import matplotlib.pyplot as plt
from collections import deque

PORT = "/dev/ttyACM0"   # adjust if needed (e.g., COM5 on Windows)
BAUD = 115200

MIN_MM, MAX_MM = 100, 6000   # distance gate; tune for your unit
STRENGTH_MIN = 10            # intensity gate; tune as needed

def parse_csv_line(line: str):
    # expecting: angle,dist,strength,flag1,flag2
    parts = line.strip().split(',')
    if len(parts) < 3:
        return None
    try:
        ang = int(parts[0]); dist = int(parts[1]); s = int(parts[2])
        return ang, dist, s
    except ValueError:
        return None

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    print(f"Listening on {PORT}@{BAUD} ...")

    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter([], [])
    ax.set_aspect('equal', 'box')
    ax.set_xlim(-6.5, 6.5)   # meters
    ax.set_ylim(-6.5, 6.5)
    ax.grid(True)
    ax.set_title("HLDS live scan (meters)")

    # Keep one revolution worth of points (simple 0-359 bucket)
    ranges_m = [float('nan')] * 360

    last_plot = time.time()
    while True:
        line = ser.readline().decode('ascii', errors='ignore')
        rec = parse_csv_line(line)
        if not rec:
            continue

        ang, dist_mm, strength = rec

        # Basic filtering
        if not (MIN_MM <= dist_mm <= MAX_MM):
            continue
        if strength < STRENGTH_MIN:
            continue

        # Store in 1° bucket
        ranges_m[ang % 360] = dist_mm / 1000.0

        # Update plot ~20 Hz
        if time.time() - last_plot > 0.05:
            xs, ys = [], []
            for a in range(360):
                r = ranges_m[a]
                if math.isnan(r):
                    continue
                th = math.radians(a)
                xs.append(r * math.cos(th))
                ys.append(r * math.sin(th))
            sc.set_offsets(list(zip(xs, ys)))
            ax.figure.canvas.draw()
            ax.figure.canvas.flush_events()
            last_plot = time.time()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
