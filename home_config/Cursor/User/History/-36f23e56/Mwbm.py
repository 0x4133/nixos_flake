 
# HLS-LFCD2 ASCII-hex stream -> points (LAS + CSV), tolerant parser (42B and 22B frames)
# - Non-blocking serial, large reads
# - Robust resync on 0xFA
# - No checksum requirement (ASCII dumps often don't match canonical checksum)
# - Keeps intensity even if 0
# - RPM estimate from index cadence (independent of device speed field)
 
import serial, math, laspy, numpy as np, time
from datetime import datetime
 
# ====== CONFIG ======
PORT = "/dev/tty.usbmodem9888E0072B9C2"
BAUD = 115200
POINT_LIMIT = 100_000     # stop after this many points; set 0 for unlimited
HEARTBEAT_SEC = 1.0
# ====================
 
FRAME42 = 42   # 6 samples per frame
FRAME22 = 22   # 4 samples per frame
 
def hex_only(bs: bytes) -> bytes:
    """Keep only ASCII hex chars (0-9A-Fa-f)."""
    return bytes(c for c in bs if (48 <= c <= 57) or (65 <= c <= 70) or (97 <= c <= 102))
 
def asciihex_to_bytes_chunk(bs: bytes) -> bytes:
    """
    Convert any chunk that may contain ASCII hex into raw bytes.
    Strips non-hex; if odd nibble count, drop last nibble.
    """
    if not bs:
        return b""
    h = hex_only(bs)
    if len(h) < 2:
        return b""
    if len(h) % 2 == 1:
        h = h[:-1]
    try:
        return bytes.fromhex(h.decode("ascii", errors="ignore"))
    except Exception:
        return b""
 
def parse42(frame: bytes):
    """Parse 42-byte LFCD2 ASCII frame (no checksum enforcement). Returns list[(x,y,z,I)] or None."""
    if len(frame) != FRAME42 or frame[0] != 0xFA:
        return None, None
    idx = frame[1]
    if not (0xA0 <= idx <= 0xF9):
        return None, None
 
    base = (idx - 0xA0) * 6
    pts = []
    for i in range(6):
        o = 4 + 6*i
        d0, d1, inten = frame[o], frame[o+1], frame[o+2]  # 1-byte intensity in your stream
        dist = d0 | (d1 << 8)  # mm
        if dist == 0 or dist > 12000:
            continue
        ang = (base + i) % 360
        r = dist / 1000.0
        a = math.radians(ang)
        pts.append((r*math.cos(a), r*math.sin(a), 0.0, int(inten)))
    return idx, pts
 
def parse22(frame: bytes):
    """Parse 22-byte XV-style frame. Returns list[(x,y,z,I)] or None."""
    if len(frame) != FRAME22 or frame[0] != 0xFA:
        return None, None
    idx = frame[1]
    if not (0xA0 <= idx <= 0xF9):
        return None, None
 
    base = (idx - 0xA0) * 4
    pts = []
    for i in range(4):
        o = 4 + 4*i
        b0, b1, b2, b3 = frame[o:o+4]
        invalid = (b1 & 0x80) != 0
        dist = ((b1 & 0x3F) << 8) | b0
        inten = (b3 << 8) | b2  # 16-bit intensity typical for XV-11 frames
        if invalid or dist == 0 or dist > 12000:
            continue
        ang = (base + i) % 360
        r = dist / 1000.0
        a = math.radians(ang)
        pts.append((r*math.cos(a), r*math.sin(a), 0.0, int(inten)))
    return idx, pts
 
def main():
    all_xyz = []
    all_I   = []
 
    # RPM estimate from index cadence (independent of device's speed field)
    last_idx = None
    rev_ticks = 0
    rpm_est = 0.0
    last_rev_t = time.time()
 
    last_hb = time.time()
    smp = frames42 = frames22 = dropped = 0
 
    with serial.Serial(PORT, BAUD, timeout=0) as ser:  # non-blocking
        print(f"[+] Reading ASCII-hex from {PORT} @ {BAUD}")
        buf = bytearray()
 
        try:
            while True:
                if POINT_LIMIT and len(all_xyz) >= POINT_LIMIT:
                    break
 
                # Large non-blocking read
                chunk = ser.read(16384)
                if chunk:
                    buf.extend(asciihex_to_bytes_chunk(chunk))
                else:
                    # Small passive wait to avoid busy spin when idle
                    time.sleep(0.001)
 
                progressed = True
                while progressed:
                    progressed = False
                    # Find next 0xFA
                    start = buf.find(b'\xFA')
                    if start < 0:
                        # Keep buffer bounded
                        if len(buf) > 16384:
                            del buf[:-64]
                        break
                    if start > 0:
                        del buf[:start]
 
                    # Prefer 42B (your stream) first
                    if len(buf) >= FRAME42 and buf[0] == 0xFA:
                        fr = bytes(buf[:FRAME42])
                        idx, pts = parse42(fr)
                        if idx is not None:
                            # RPM estimate via index cadence
                            now = time.time()
                            if last_idx is not None:
                                step = (idx - last_idx) & 0xFF
                                if step > 0:
                                    rev_ticks += step
                                    if rev_ticks >= (0xF9 - 0xA0 + 1):  # ~one revolution worth of indexes
                                        dt = now - last_rev_t
                                        if dt > 0:
                                            rpm_est = 60.0 / dt
                                        rev_ticks = 0
                                        last_rev_t = now
                            last_idx = idx
 
                            if pts:
                                for x, y, z, I in pts:
                                    all_xyz.append((x, y, z))
                                    all_I.append(I)
                                    smp += 1
                            frames42 += 1
                            del buf[:FRAME42]
                            progressed = True
                            continue
 
                    # Try 22B fallback
                    if len(buf) >= FRAME22 and buf[0] == 0xFA:
                        fr = bytes(buf[:FRAME22])
                        idx, pts = parse22(fr)
                        if idx is not None:
                            # RPM cadence still works (indexes advance)
                            now = time.time()
                            if last_idx is not None:
                                step = (idx - last_idx) & 0xFF
                                if step > 0:
                                    rev_ticks += step
                                    if rev_ticks >= (0xF9 - 0xA0 + 1):
                                        dt = now - last_rev_t
                                        if dt > 0:
                                            rpm_est = 60.0 / dt
                                        rev_ticks = 0
                                        last_rev_t = now
                            last_idx = idx
 
                            if pts:
                                for x, y, z, I in pts:
                                    all_xyz.append((x, y, z))
                                    all_I.append(I)
                                    smp += 1
                            frames22 += 1
                            del buf[:FRAME22]
                            progressed = True
                            continue
 
                    # Couldn’t parse either; drop one byte to resync
                    if len(buf) > 0:
                        del buf[0:1]
                        dropped += 1
                        progressed = True
 
                # Heartbeat
                now = time.time()
                if now - last_hb >= HEARTBEAT_SEC:
                    print(f"[stats] samples/s≈{smp:4d}  f42={frames42:3d}  f22={frames22:3d}  drop={dropped:3d}  rpm≈{rpm_est:6.1f}  totalPts={len(all_xyz)}")
                    smp = 0; frames42 = 0; frames22 = 0; dropped = 0
                    last_hb = now
 
        except KeyboardInterrupt:
            print("\n[!] Stopping…")
 
    # Write outputs
    n = len(all_xyz)
    print(f"[+] Writing {n} points")
    if n == 0:
        print("[!] No points captured.")
        return
 
    pts = np.asarray(all_xyz, dtype=np.float32)
    intensity = np.asarray(all_I, dtype=np.uint16)
 
    # LAS
    hdr = laspy.LasHeader(point_format=3, version="1.2")
    las = laspy.LasData(hdr)
    las.x, las.y, las.z = pts[:,0], pts[:,1], pts[:,2]
    las.intensity = intensity
    out_base = f"lidar_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    las_file = f"{out_base}.las"
    las.write(las_file)
    print(f"[✓] Saved {las_file}")
 
    # CSV
    csv_file = f"{out_base}.csv"
    with open(csv_file, "w") as f:
        f.write("x,y,z,intensity\n")
        for (x,y,z), I in zip(all_xyz, all_I):
            f.write(f"{x},{y},{z},{I}\n")
    print(f"[✓] Saved {csv_file}")
 
if __name__ == "__main__":
    main()
