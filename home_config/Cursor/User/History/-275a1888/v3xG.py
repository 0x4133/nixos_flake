#!/usr/bin/env python3
import serial, math, time, sys
import tkinter as tk

PORT = "/dev/ttyACM0"   # adjust if needed (e.g., COM5 on Windows)
BAUD = 115200

MIN_MM, MAX_MM = 100, 6000   # distance gate; tune for your unit
STRENGTH_MIN = 10            # intensity gate; tune as needed

# Canvas/world settings
METERS_VIEW = 6.5            # half-span in meters (± this, both axes)
PX_SIZE = 700                # canvas width/height in pixels
POINT_RADIUS_PX = 2          # dot radius

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

class LidarCanvas:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=PX_SIZE, height=PX_SIZE, bg="white")
        self.canvas.pack()
        self.center = PX_SIZE // 2
        self.scale = (PX_SIZE // 2) / METERS_VIEW  # px per meter

        # background grid + crosshairs
        self._draw_axes()

        # storage for one revolution (meters or None)
        self.ranges_m = [None] * 360

        # cache of canvas item IDs for each degree (optional micro-optimization)
        self.items = [None] * 360

    def _draw_axes(self):
        c = self.canvas
        cx = cy = self.center
        # crosshairs
        c.create_line(0, cy, PX_SIZE, cy, fill="#ddd")
        c.create_line(cx, 0, cx, PX_SIZE, fill="#ddd")
        # range rings (every 1m)
        for m in range(1, int(METERS_VIEW)+1):
            r = int(m * self.scale)
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#eee")

        c.create_text(10, 10, anchor="nw", text="HLDS live scan (meters)", fill="#555")

    def set_range(self, ang_deg: int, r_m: float):
        self.ranges_m[ang_deg % 360] = r_m

    def _world_to_canvas(self, x_m: float, y_m: float):
        # world coords: meters, +x right, +y up; canvas y is down
        cx = cy = self.center
        return (cx + x_m * self.scale, cy - y_m * self.scale)

    def redraw(self):
        # Update/refresh all points
        for a in range(360):
            r = self.ranges_m[a]
            item = self.items[a]
            if r is None:
                # remove stale dot if present
                if item is not None:
                    self.canvas.delete(item)
                    self.items[a] = None
                continue

            th = math.radians(a)
            x = r * math.cos(th)
            y = r * math.sin(th)
            px, py = self._world_to_canvas(x, y)
            rpx = POINT_RADIUS_PX
            if item is None:
                self.items[a] = self.canvas.create_oval(
                    px - rpx, py - rpx, px + rpx, py + rpx,
                    outline="", fill="black"
                )
            else:
                # move existing dot
                self.canvas.coords(item, px - rpx, py - rpx, px + rpx, py + rpx)

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.05)
    except Exception as e:
        print(f"Failed to open {PORT}@{BAUD}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Listening on {PORT}@{BAUD} ... (press Ctrl+C in terminal to quit)")

    root = tk.Tk()
    root.title("HLDS live scan (no NumPy)")
    view = LidarCanvas(root)

    last_plot = time.time()

    def pump():
        nonlocal last_plot
        # Read and process multiple lines per tick
        for _ in range(200):  # small batch to keep UI responsive
            try:
                line = ser.readline()
            except Exception:
                break

            if not line:
                break

            rec = parse_csv_line(line.decode('ascii', errors='ignore'))
            if not rec:
                continue

            ang, dist_mm, strength = rec

            # filtering
            if dist_mm < MIN_MM or dist_mm > MAX_MM:
                continue
            if strength < STRENGTH_MIN:
                continue

            view.set_range(ang % 360, dist_mm / 1000.0)

        # ~20 Hz redraw
        now = time.time()
        if now - last_plot > 0.05:
            view.redraw()
            last_plot = now

        # schedule next tick
        root.after(10, pump)

    root.after(10, pump)
    try:
        root.mainloop()
    finally:
        try:
            ser.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
