#!/usr/bin/env python3
import serial
import sys
import math
import time
from collections import deque

PORT = "/dev/ttyACM0"   # adjust if needed (e.g., COM5 on Windows)
BAUD = 115200

MIN_MM, MAX_MM = 100, 6000   # distance gate; tune for your unit
STRENGTH_MIN = 10            # intensity gate; tune as needed

def parse_csv_line(line: str):
    """
    Parse CSV line from LIDAR: angle,dist,strength,flag1,flag2
    """
    parts = line.strip().split(',')
    if len(parts) < 3:
        return None
    try:
        ang = int(parts[0])
        dist = int(parts[1])
        strength = int(parts[2])
        return ang, dist, strength
    except ValueError:
        return None

def print_radar_display(ranges_m, rpm, secs_since_frame, bytes_waiting, total_bytes, note):
    """
    Print a simple ASCII radar display with status
    """
    print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
    print(f"LIDAR RPM: {rpm}")
    print(f"Status: last_frame={secs_since_frame:.1f}s ago, in_waiting={bytes_waiting}, total_bytes={total_bytes} {note}")
    print("Radar Display (meters):")
    print("=" * 50)
    
    # Create a simple circular display
    for y in range(20, -21, -1):
        line = ""
        for x in range(-30, 31):
            if x == 0 and y == 0:
                line += "O"  # Center point
            elif x == 0:
                line += "|"  # Vertical line
            elif y == 0:
                line += "-"  # Horizontal line
            else:
                # Calculate angle and distance for this position
                angle = math.degrees(math.atan2(y, x)) % 360
                if angle < 0:
                    angle += 360
                
                # Get distance at this angle
                dist = ranges_m[int(angle)]
                if not math.isnan(dist):
                    # Calculate expected distance for this position
                    expected_dist = math.sqrt(x*x + y*y) * 0.1  # Scale factor
                    if abs(dist - expected_dist) < 0.5:  # Within 0.5m
                        line += "*"  # Object detected
                    else:
                        line += " "
                else:
                    line += " "
        print(line)
    
    print("=" * 50)
    print("O = Sensor, * = Object, |/- = Axes")

def start_motor(ser: serial.Serial):
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass
    # Try different start commands for different LIDAR models
    for cmd in [b'b', b's', b'g']:
        ser.write(cmd)
        time.sleep(0.1)

def stop_motor(ser: serial.Serial):
    try:
        for cmd in [b'e', b'x', b'q']:
            ser.write(cmd)
            time.sleep(0.05)
    except Exception:
        pass

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.02)
        # Toggle DTR to nudge ACM devices
        try:
            ser.dtr = False
            time.sleep(0.05)
            ser.dtr = True
        except Exception:
            pass
        print(f"Listening on {PORT}@{BAUD} ...")
        
        # Ensure motor is running
        start_motor(ser)
        print("Starting LIDAR motor...")
        time.sleep(0.2)
        try:
            ser.reset_input_buffer()
        except Exception:
            pass
        
        # Keep one revolution worth of points (simple 0-359 bucket)
        ranges_m = [float('nan')] * 360
        
        last_display = time.time()
        last_frame_time = 0.0
        last_status_time = 0.0
        total_bytes = 0
        note = ""
        print("Reading CSV data... Press Ctrl+C to stop")
        
        while True:
            try:
                line = ser.readline()
                if line:
                    total_bytes += len(line)
                    line_str = line.decode('ascii', errors='ignore').strip()
                    
                    if line_str:
                        result = parse_csv_line(line_str)
                        if result:
                            ang, dist_mm, strength = result
                            last_frame_time = time.time()
                            
                            # Basic filtering
                            if MIN_MM <= dist_mm <= MAX_MM and strength >= STRENGTH_MIN:
                                ranges_m[ang % 360] = dist_mm / 1000.0  # Convert to meters
                
                now = time.time()
                # Build a short status note
                secs_since_frame = (now - last_frame_time) if last_frame_time else float('inf')
                bytes_waiting = 0
                try:
                    bytes_waiting = ser.in_waiting
                except Exception:
                    pass
                note = ""
                if secs_since_frame > 2.0:
                    note = "(no frames >2s, re-sending start)"
                    if now - last_status_time > 1.0:
                        start_motor(ser)
                        last_status_time = now
                
                # Show display periodically
                if now - last_display > 0.5:
                    rpm_display = 0 if last_frame_time == 0 else 0  # CSV format doesn't have RPM
                    print_radar_display(ranges_m, rpm_display, secs_since_frame, bytes_waiting, total_bytes, note)
                    last_display = now
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Log and continue; avoid silent hang
                print(f"Error reading data: {e}")
                time.sleep(0.1)
                continue
                
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        print(f"Make sure {PORT} exists and you have permission to access it.")
        sys.exit(1)
    finally:
        if 'ser' in locals():
            stop_motor(ser)
            ser.close()
        print("\nLIDAR scan stopped.")

if __name__ == "__main__":
    main()
