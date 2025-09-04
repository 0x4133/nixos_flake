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

def parse_lidar_data(data):
    """
    Parse the LIDAR data format from the HLS-LFCD2
    """
    if len(data) != 42 or data[0] != 250:
        return None
    
    bytes_data = list(data)
    degree = (bytes_data[1] - 0xA0) * 6
    rpm = (bytes_data[3] << 8) | bytes_data[2]
    
    # basic checksum/validity used by reference implementation
    if bytes_data[41] != bytes_data[40] or bytes_data[40] == 0:
        return None
    
    readings = []
    for i in range(6):
        distance = (bytes_data[2 + (i*4)+3] << 8) | (bytes_data[2 + (i*4)+2])
        intensity = (bytes_data[2 + (i*4)+1] << 8) | (bytes_data[2 + (i*4)+0])
        angle = degree + i
        if 0 <= angle < 360:
            readings.append((angle, distance, intensity))
    
    return readings, rpm

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
    # HLDS expects 'b' to start; send a short sequence
    for _ in range(3):
        ser.write(b'b')
        time.sleep(0.05)

def stop_motor(ser: serial.Serial):
    try:
        for _ in range(2):
            ser.write(b'e')
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
        
        buffer = bytearray()
        last_display = time.time()
        last_frame_time = 0.0
        last_status_time = 0.0
        total_bytes = 0
        note = ""
        print("Reading frames... Press Ctrl+C to stop")
        
        while True:
            try:
                chunk = ser.read(256)
                if chunk:
                    buffer.extend(chunk)
                    total_bytes += len(chunk)
                    # Debug: show first few bytes occasionally
                    if total_bytes % 1000 < len(chunk):
                        print(f"Debug: First 16 bytes of chunk: {chunk[:16].hex()}")
                        print(f"Debug: Buffer size: {len(buffer)}, looking for 0xFA...")
                        if len(buffer) > 0:
                            print(f"Debug: First 16 bytes in buffer: {buffer[:16].hex()}")
                            fa_pos = buffer.find(b"\xFA")
                            print(f"Debug: 0xFA found at position: {fa_pos}")
                
                # Try to extract frames starting at 0xFA
                processed_any = False
                resyncs = 0
                while True:
                    idx = buffer.find(b"\xFA")
                    if idx == -1:
                        # No start byte in buffer; keep buffer from growing unbounded
                        if len(buffer) > 4096:
                            buffer.clear()
                        break
                    if idx > 0:
                        # Drop noise before header
                        del buffer[:idx]
                        resyncs += 1
                        if resyncs > 10:
                            break
                    if len(buffer) < 42:
                        break
                    frame = bytes(buffer[:42])
                    del buffer[:42]
                    result = parse_lidar_data(frame)
                    if result:
                        processed_any = True
                        readings, rpm = result
                        last_frame_time = time.time()
                        for angle, dist_mm, strength in readings:
                            if MIN_MM <= dist_mm <= MAX_MM and strength >= STRENGTH_MIN:
                                ranges_m[angle] = dist_mm / 1000.0
                
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
                    rpm_display = 0 if last_frame_time == 0 else rpm
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
