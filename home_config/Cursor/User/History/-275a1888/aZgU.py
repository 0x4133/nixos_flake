#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import numpy as np
from numpy.typing import NDArray
try:
    from scipy.signal import find_peaks
except Exception:
    find_peaks = None

def load_iq(path: str) -> NDArray[np.complex64]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".npy":
        x = np.load(path)
        if not np.iscomplexobj(x):
            raise ValueError(".npy must contain complex dtype")
        return x.astype(np.complex64, copy=False)
    if ext == ".c8":
        raw = np.fromfile(path, dtype=np.int8)
        if raw.size % 2 != 0:
            raw = raw[:-1]
        iq = raw.reshape(-1, 2).astype(np.float32) / 127.0
        return (iq[:, 0] + 1j * iq[:, 1]).astype(np.complex64)
    if ext == ".wav":
        import wave, struct
        with wave.open(path, 'rb') as w:
            if w.getnchannels() < 2:
                raise ValueError("wav must be stereo (I in L, Q in R)")
            n = w.getnframes()
            sampwidth = w.getsampwidth()
            raw = w.readframes(n)
            if sampwidth == 2:
                fmt = f"<{n * w.getnchannels()}h"
                data = np.array(struct.unpack(fmt, raw), dtype=np.float32) / 32768.0
            elif sampwidth == 4:
                fmt = f"<{n * w.getnchannels()}f"
                data = np.array(struct.unpack(fmt, raw), dtype=np.float32)
            else:
                raise ValueError("unsupported WAV sample width")
            data = data.reshape(n, w.getnchannels())
            i = data[:, 0]
            q = data[:, 1]
            return (i + 1j * q).astype(np.complex64)
    raise ValueError(f"unsupported file extension: {ext}")

def moving_avg(x: NDArray[np.float32], m: int) -> NDArray[np.float32]:
    if m <= 1:
        return x
    k = np.ones(m, dtype=np.float32) / m
    return np.convolve(x, k, mode='same')

@dataclass
class Burst:
    start: int
    end: int
    peak_snr_db: float

def detect_bursts(iq: NDArray[np.complex64], fs: float, min_burst_ms: float = 1.0,
                  guard_ms: float = 0.2, smooth_ms: float = 0.2, thresh_db: float = 6.0) -> List[Burst]:
    p = (np.abs(iq) ** 2).astype(np.float32)
    win = max(1, int(smooth_ms * 1e-3 * fs))
    ps = moving_avg(p, win)
    med = np.median(ps + 1e-12)
    thresh = med * (10 ** (thresh_db / 10.0))
    above = ps > thresh
    idx = np.flatnonzero(np.diff(above.astype(np.int8), prepend=0))
    segs: List[Tuple[int, int]] = []
    active = False
    s = 0
    for i in idx:
        if not active and above[i]:
            s = i
            active = True
        elif active and not above[i]:
            segs.append((s, i))
            active = False
    if active:
        segs.append((s, len(above) - 1))
    g = int(guard_ms * 1e-3 * fs)
    min_len = int(min_burst_ms * 1e-3 * fs)
    out: List[Burst] = []
    prev: Optional[Tuple[int, int]] = None
    for (a, b) in segs:
        a = max(0, a - g)
        b = min(len(iq) - 1, b + g)
        if prev and a - prev[1] < 2 * g:
            prev = (prev[0], b)
        else:
            if prev:
                if prev[1] - prev[0] >= min_len:
                    sl = slice(prev[0], prev[1])
                    snr = 10 * np.log10((ps[sl].max() + 1e-12) / (med + 1e-12))
                    out.append(Burst(prev[0], prev[1], float(snr)))
            prev = (a, b)
    if prev and prev[1] - prev[0] >= min_len:
        sl = slice(prev[0], prev[1])
        snr = 10 * np.log10((ps[sl].max() + 1e-12) / (med + 1e-12))
        out.append(Burst(prev[0], prev[1], float(snr)))
    return out

def robust_burst_find(iq: NDArray[np.complex64], fs: float, *,
                      min_burst_ms: float = 1.0,
                      thresh_db: float = 6.0,
                      smooth_ms: float = 0.2,
                      guard_ms: float = 0.2) -> List[Burst]:
    b = detect_bursts(iq, fs, min_burst_ms=min_burst_ms, guard_ms=guard_ms, smooth_ms=smooth_ms, thresh_db=thresh_db)
    if b:
        return b
    for td in [thresh_db - d for d in (3, 6, 9, 12, 18)]:
        for sm in (smooth_ms, 0.5, 1.0, 2.0):
            b = detect_bursts(iq, fs, min_burst_ms=min_burst_ms, guard_ms=guard_ms, smooth_ms=sm, thresh_db=td)
            if b:
                return b
    p = (np.abs(iq) ** 2).astype(np.float32)
    med = float(np.median(p + 1e-12))
    snr = 10.0 * math.log10((float(np.max(p)) + 1e-12) / (med + 1e-12))
    return [Burst(0, len(iq) - 1, snr)]

def _autocorr(x: NDArray[np.float32]) -> NDArray[np.float32]:
    x = x - np.mean(x)
    n = len(x)
    f = np.fft.rfft(x, n=1 << (n - 1).bit_length())
    ac = np.fft.irfft(np.abs(f) ** 2)[:n]
    ac /= (np.arange(n, 0, -1))
    return ac.astype(np.float32)

@dataclass
class BaudEstimate:
    baud: float
    score: float

def estimate_baud(iq: NDArray[np.complex64], fs: float, baud_min: float = 100, baud_max: float = 10000) -> BaudEstimate:
    amp = np.abs(iq).astype(np.float32)
    ph = np.unwrap(np.angle(iq)).astype(np.float32)
    dph = np.diff(ph, prepend=ph[0])
    feat = 0.5 * (amp / (np.max(amp) + 1e-6)) + 0.5 * (np.abs(dph) / (np.max(np.abs(dph)) + 1e-6))
    ac = _autocorr(feat)
    lag_min = int(fs / baud_max)
    lag_max = max(lag_min + 1, int(fs / baud_min))
    roi = ac[lag_min:lag_max]
    if roi.size < 4:
        return BaudEstimate(baud=round((baud_min + baud_max) / 2, 2), score=0.0)
    if find_peaks is None:
        k = np.argmax(roi) + lag_min
    else:
        peaks, _ = find_peaks(roi, distance=max(1, (lag_max - lag_min) // 32))
        if len(peaks) == 0:
            k = np.argmax(roi) + lag_min
        else:
            peak_vals = roi[peaks]
            k = int(peaks[np.argmax(peak_vals)]) + lag_min
    period = max(1, k)
    baud = fs / period
    score = float((roi[k - lag_min] - np.median(roi)) / (np.max(roi) - np.min(roi) + 1e-9))
    score = max(0.0, min(1.0, score))
    return BaudEstimate(baud=float(baud), score=score)

def sample_symbols(iq: NDArray[np.complex64], fs: float, baud: float, start_phase: float = 0.0) -> NDArray[np.complex64]:
    step = fs / baud
    n_sym = int(len(iq) / step)
    idx = (np.arange(n_sym, dtype=np.float64) * step + start_phase * step).astype(np.int64)
    idx = np.clip(idx, 0, len(iq) - 1)
    return iq[idx].astype(np.complex64)

@dataclass
class Symbolization:
    labels: NDArray[np.int32]
    centroids: NDArray[np.complex64]
    bits_per_sym: int
    score: float

def kmeans_complex(x: NDArray[np.complex64], k: int, iters: int = 30, seed: int = 0) -> Tuple[NDArray[np.complex64], NDArray[np.int32], float]:
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(x), size=k, replace=False)
    c = x[idx].astype(np.complex64).copy()
    lab = np.zeros(len(x), dtype=np.int32)
    for _ in range(iters):
        d = np.abs(x[:, None] - c[None, :])
        lab = np.argmin(d, axis=1).astype(np.int32)
        for j in range(k):
            sel = x[lab == j]
            if sel.size:
                c[j] = np.mean(sel)
    inertia = float(np.sum(np.abs(x - c[lab]) ** 2))
    sep = float(np.min(np.abs(c[:, None] - c[None, :] + np.eye(k) * 1e9))) if k > 1 else 0.0
    score = sep / (inertia / (len(x) + 1e-9) + 1e-9)
    return c, lab, score

def discover_symbols(sym: NDArray[np.complex64], k_min: int = 2, k_max: int = 8) -> Symbolization:
    best = None
    best_k = None
    best_c = None
    best_lab = None
    for k in range(k_min, k_max + 1):
        c, lab, score = kmeans_complex(sym, k)
        if best is None or score > best:
            best = score
            best_k = k
            best_c = c
            best_lab = lab
    bits = int(math.ceil(math.log2(best_k))) if best_k else 1
    return Symbolization(labels=best_lab, centroids=best_c.astype(np.complex64), bits_per_sym=bits, score=float(best or 0.0))

def pack_bits_to_bytes(labels: NDArray[np.int32], bits_per_sym: int) -> NDArray[np.uint8]:
    if bits_per_sym <= 0:
        return np.zeros(0, dtype=np.uint8)
    labels_u = labels.astype(np.uint16)
    bit_slices = [((labels_u >> b) & 1).astype(np.uint8) for b in range(bits_per_sym)]
    bits = np.stack(bit_slices, axis=1).reshape(-1)
    pad = (-len(bits)) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    return np.packbits(bits, bitorder='little').astype(np.uint8)

@dataclass
class Frame:
    offset: int
    raw_bytes: NDArray[np.uint8]

def slice_frames_from_bursts(bursts: List[Burst], labels: NDArray[np.int32], bits_per_sym: int,
                             sym_per_sample: float) -> List[Frame]:
    frames: List[Frame] = []
    for b in bursts:
        sym_start = int(b.start * sym_per_sample)
        sym_end = int(b.end * sym_per_sample)
        sub_labels = labels[sym_start:sym_end]
        if len(sub_labels) < (8 // max(1, bits_per_sym)):
            continue
        bytes_arr = pack_bits_to_bytes(sub_labels, bits_per_sym)
        frames.append(Frame(offset=b.start, raw_bytes=bytes_arr))
    return frames

def cluster_frames(frames: List[Frame], head_bytes: int = 6) -> Dict[int, List[Frame]]:
    buckets: Dict[int, List[Frame]] = {}
    for fr in frames:
        hlen = min(head_bytes, len(fr.raw_bytes))
        if hlen >= 8:
            head64 = int(np.frombuffer(fr.raw_bytes[:8].tobytes(), dtype=np.uint64)[0])
        else:
            head64 = int.from_bytes(fr.raw_bytes[:hlen].tobytes(), 'little')
        key = (len(fr.raw_bytes) << 16) ^ head64
        buckets.setdefault(key, []).append(fr)
    bylen: Dict[int, List[Frame]] = {}
    for _, lst in buckets.items():
        if len(lst) < 3:
            bylen.setdefault(len(lst[0].raw_bytes), []).extend(lst)
    for l, lst in bylen.items():
        buckets[l] = lst
    return buckets

def entropy(arr: NDArray[np.uint8]) -> float:
    _, counts = np.unique(arr, return_counts=True)
    p = counts.astype(np.float64) / np.sum(counts)
    return float(-(p * np.log2(p + 1e-12)).sum())

def position_entropy(frames: List[Frame], max_len: int = 512) -> NDArray[np.float32]:
    L = min(max_len, max(len(f.raw_bytes) for f in frames))
    ent = np.zeros(L, dtype=np.float32)
    for i in range(L):
        col = [f.raw_bytes[i] for f in frames if i < len(f.raw_bytes)]
        if len(col) >= 2:
            ent[i] = entropy(np.array(col, dtype=np.uint8))
        else:
            ent[i] = 8.0
    return ent

def mutual_info(x: NDArray[np.uint8], y: NDArray[np.uint8]) -> float:
    vx, cx = np.unique(x, return_counts=True)
    vy, cy = np.unique(y, return_counts=True)
    px = cx / cx.sum()
    py = cy / cy.sum()
    xy = x.astype(np.uint32) * 257 + y.astype(np.uint32)
    vxy, cxy = np.unique(xy, return_counts=True)
    pxy = cxy / cxy.sum()
    px_map = {int(v): float(p) for v, p in zip(vx, px)}
    py_map = {int(v): float(p) for v, p in zip(vy, py)}
    mi = 0.0
    for v, p in zip(vxy, pxy):
        xi = int(v // 257)
        yi = int(v % 257)
        mi += float(p * math.log2(p / (px_map.get(xi, 1e-12) * py_map.get(yi, 1e-12) + 1e-12) + 1e-12))
    return max(0.0, mi)

CRC16_POLYS = {
    "IBM": 0xA001,
    "CCITT": 0x1021,
}

def crc16(data: NDArray[np.uint8], poly: int = 0x1021, init: int = 0xFFFF, refin: bool = False, refout: bool = False, xorout: int = 0x0000) -> int:
    def rev8(b: int) -> int:
        return int('{:08b}'.format(b)[::-1], 2)
    reg = init & 0xFFFF
    for b in data.tolist():
        if refin:
            b = rev8(b)
        reg ^= (b << 8)
        for _ in range(8):
            if reg & 0x8000:
                reg = ((reg << 1) & 0xFFFF) ^ poly
            else:
                reg = (reg << 1) & 0xFFFF
    if refout:
        reg = int('{:016b}'.format(reg)[::-1], 2)
    return (reg ^ xorout) & 0xFFFF

def checksum_hypotheses(frames: List[Frame]) -> List[Dict[str, object]]:
    hyps: List[Dict[str, object]] = []
    hits = total = 0
    for f in frames:
        if len(f.raw_bytes) <= 2:
            continue
        body = f.raw_bytes[:-1]
        chk = f.raw_bytes[-1]
        total += 1
        if (int(np.sum(body, dtype=np.uint32)) & 0xFF) == int(chk):
            hits += 1
    if total:
        hyps.append({"type": "sum8_tail1", "tail": 1, "hit_rate": hits / total})
    for name, poly in CRC16_POLYS.items():
        for endian in ("big", "little"):
            hits = total = 0
            for f in frames:
                if len(f.raw_bytes) <= 4:
                    continue
                body = f.raw_bytes[:-2]
                chk = int.from_bytes(f.raw_bytes[-2:].tobytes(), endian)
                total += 1
                c = crc16(body, poly=poly, init=0xFFFF, refin=(name == "IBM"), refout=(name == "IBM"))
                if c == chk:
                    hits += 1
            if total:
                hyps.append({"type": f"crc16_{name}_{endian}", "tail": 2, "hit_rate": hits / total})
    try:
        import zlib
        for endian in ("big", "little"):
            hits = total = 0
            for f in frames:
                if len(f.raw_bytes) <= 8:
                    continue
                body = f.raw_bytes[:-4]
                chk = int.from_bytes(f.raw_bytes[-4:].tobytes(), endian)
                total += 1
                c = zlib.crc32(body.tobytes()) & 0xFFFFFFFF
                if c == chk:
                    hits += 1
            if total:
                hyps.append({"type": f"crc32_ieee_{endian}", "tail": 4, "hit_rate": hits / total})
    except Exception:
        pass
    hyps.sort(key=lambda d: d["hit_rate"], reverse=True)
    return hyps

def length_hypotheses(frames: List[Frame], max_search: int = 8) -> List[Dict[str, object]]:
    hyps: List[Dict[str, object]] = []
    min_front = min(len(f.raw_bytes) for f in frames)
    for width in [1, 2]:
        limit = max(0, min(max_search, min_front) - width)
        for off in range(0, limit):
            hits = tot = 0
            for f in frames:
                if len(f.raw_bytes) < off + width:
                    continue
                for tail in [0, 1, 2, 4]:
                    if len(f.raw_bytes) < off + width + 1 + tail:
                        continue
                    val = int.from_bytes(f.raw_bytes[off:off+width].tobytes(), 'big')
                    payload_len = len(f.raw_bytes) - (off + width) - tail
                    if payload_len < 0:
                        continue
                    tot += 1
                    if val == payload_len:
                        hits += 1
            if tot:
                hyps.append({"offset": off, "width": width, "hit_rate": hits / tot})
    hyps.sort(key=lambda d: d["hit_rate"], reverse=True)
    return hyps

def propose_grammar(frames: List[Frame]) -> Dict[str, object]:
    ent = position_entropy(frames)
    header_end = int(np.argmax(ent > np.median(ent) + 0.5))
    header_end = max(0, header_end)
    len_h = length_hypotheses(frames)
    chk_h = checksum_hypotheses(frames)
    guess = {
        "header_bytes": header_end,
        "length_field": len_h[0] if len_h else None,
        "checksum": chk_h[0] if chk_h else None,
        "field_entropy_bits": ent.tolist(),
        "frame_lengths": [len(f.raw_bytes) for f in frames],
    }
    return guess

def write_kaitai(guess: Dict[str, object], out_path: str):
    hdr = int(guess.get("header_bytes") or 0)
    lenf = guess.get("length_field") or {"offset": None, "width": None}
    chk = guess.get("checksum") or {"tail": None, "type": None}
    ksy = f"""meta:
  id: unknown_rf
  endian: be
seq:
  - id: header
    size: {hdr}
"""
    if lenf.get("offset") is not None:
        ksy += f"  - id: length\n    type: u{lenf['width']*8}\n"
        ksy += f"  - id: payload\n    size: length\n"
    else:
        ksy += f"  - id: payload\n    size: _io.size - {hdr + (chk.get('tail') or 0)}\n"
    if chk.get("tail"):
        if chk.get("tail") == 2 and str(chk.get("type", "")).startswith("crc16"):
            ksy += f"  - id: crc\n    type: u16\n"
        elif chk.get("tail") == 4:
            ksy += f"  - id: crc\n    type: u32\n"
    with open(out_path, 'w') as f:
        f.write(ksy)

def _lua_uint_field(width_bytes: Optional[int]) -> str:
    if width_bytes == 1:
        return "ProtoField.uint8"
    if width_bytes == 2:
        return "ProtoField.uint16"
    if width_bytes == 4:
        return "ProtoField.uint32"
    return "ProtoField.uint16"

def write_wireshark_lua(guess: Dict[str, object], out_path: str):
    hdr = int(guess.get("header_bytes") or 0)
    lenf = guess.get("length_field") or {"offset": None, "width": None}
    chk = guess.get("checksum") or {"tail": 0}
    len_pf_ctor = _lua_uint_field(lenf.get('width'))
    len_off = (lenf.get('offset') if lenf.get('offset') is not None else -1)
    len_width = (lenf.get('width') if lenf.get('width') is not None else 0)
    lua = f"""local p_unk = Proto("unknown_rf", "Unknown RF")
local f_header = ProtoField.bytes("unknown_rf.header", "Header")
local f_length = {len_pf_ctor}("unknown_rf.length", "Length", base.DEC)
local f_payload = ProtoField.bytes("unknown_rf.payload", "Payload")
local f_crc = ProtoField.bytes("unknown_rf.crc", "Checksum")
p_unk.fields = {{f_header, f_length, f_payload, f_crc}}

function p_unk.dissector(tvb, pinfo, tree)
  pinfo.cols.protocol = p_unk.name
  local root = tree:add(p_unk, tvb())
  local off = 0
  if {hdr} > 0 then
    root:add(f_header, tvb(off, {hdr}))
    off = off + {hdr}
  end
  local length = nil
  local payload_start = off
  local len_off = {len_off}
  local len_width = {len_width}
  if len_off >= 0 and len_width > 0 then
    length = tvb(len_off, len_width):uint()
    root:add(f_length, tvb(len_off, len_width))
    payload_start = len_off + len_width
  end
  local payload_len = (length ~= nil) and length or (tvb:len() - payload_start - {chk.get('tail',0)})
  root:add(f_payload, tvb(payload_start, payload_len))
  local off_crc = payload_start + payload_len
  if {chk.get('tail',0)} > 0 then
    root:add(f_crc, tvb(off_crc, {chk.get('tail',0)}))
  end
end
"""
    with open(out_path, 'w') as f:
        f.write(lua)

def run(path: str, fs: float, outdir: str, baud_min: float, baud_max: float, min_burst_ms: float):
    os.makedirs(outdir, exist_ok=True)
    iq = load_iq(path)
    iq = iq - np.mean(iq)
    iq = iq / (np.max(np.abs(iq)) + 1e-9)
    bursts = robust_burst_find(iq, fs, min_burst_ms=min_burst_ms)
    best_b = max(bursts, key=lambda b: b.peak_snr_db)
    be = estimate_baud(iq[best_b.start:best_b.end], fs, baud_min=baud_min, baud_max=baud_max)
    sym = sample_symbols(iq, fs, be.baud)
    symz = discover_symbols(sym)
    sym_per_sample = be.baud / fs
    frames = slice_frames_from_bursts(bursts, symz.labels, symz.bits_per_sym, sym_per_sample)
    if not frames:
        frames = [Frame(offset=0, raw_bytes=pack_bits_to_bytes(symz.labels, symz.bits_per_sym))]
    clusters = cluster_frames(frames)
    largest_key = max(clusters.keys(), key=lambda k: len(clusters[k]))
    canon = clusters[largest_key]
    with open(os.path.join(outdir, 'frames.bin'), 'wb') as f:
        for fr in canon:
            f.write(fr.raw_bytes.tobytes())
    meta = [{"offset": fr.offset, "length": len(fr.raw_bytes)} for fr in canon]
    with open(os.path.join(outdir, 'frames.json'), 'w') as f:
        json.dump(meta, f, indent=2)
    guess = propose_grammar(canon)
    guess.update({
        "baud": be.baud,
        "baud_score": be.score,
        "kmeans_score": symz.score,
        "bits_per_sym": symz.bits_per_sym,
        "centroids": [[float(c.real), float(c.imag)] for c in symz.centroids.tolist()],
    })
    with open(os.path.join(outdir, 'grammar_guess.json'), 'w') as f:
        json.dump(guess, f, indent=2)
    write_kaitai(guess, os.path.join(outdir, 'unknown_rf.ksy'))
    write_wireshark_lua(guess, os.path.join(outdir, 'dissector_unknown_rf.lua'))
    print("\n=== AUTOPSY SUMMARY ===")
    print(f"bursts: {len(bursts)} (top SNR≈{best_b.peak_snr_db:.1f} dB)")
    print(f"baud: {be.baud:.1f} sym/s (score {be.score:.2f})")
    print(f"constellation: {len(symz.centroids)} levels, {symz.bits_per_sym} b/sym (score {symz.score:.2f})")
    print(f"frames in top cluster: {len(canon)} (len range: {min(len(f.raw_bytes) for f in canon)}..{max(len(f.raw_bytes) for f in canon)})")
    lf = guess.get('length_field')
    cf = guess.get('checksum')
    print(f"length hypothesis: {lf}")
    print(f"checksum hypothesis: {cf}")
    print(f"Artifacts in: {outdir}")

def _bpsk_modulate(bitstream: NDArray[np.uint8], fs: float, baud: float, fc_hz: float = 0.0) -> NDArray[np.complex64]:
    sps = int(round(fs / baud))
    bits = (bitstream * 2 - 1).astype(np.float32)
    base = np.repeat(bits, sps)
    t = np.arange(base.size, dtype=np.float32) / fs
    if fc_hz != 0.0:
        carrier = np.exp(1j * 2 * np.pi * fc_hz * t).astype(np.complex64)
    else:
        carrier = np.ones_like(base, dtype=np.complex64)
    return (base.astype(np.complex64) * carrier)

def _bytes_to_bits_be(arr: NDArray[np.uint8]) -> NDArray[np.uint8]:
    return np.unpackbits(arr, bitorder='big')

def generate_demo_capture(outdir: str, fs: float = 1_000_000.0, baud: float = 2_000.0, n_frames: int = 6) -> Tuple[str, float]:
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(0)
    frames: List[bytes] = []
    for _ in range(n_frames):
        header = bytes([0xAA, 0xAA, 0x55, 0x55])
        payload = rng.integers(0, 256, size=rng.integers(8, 20), dtype=np.uint8).tobytes()
        length = len(payload).to_bytes(1, 'big')
        body = header + length + payload
        crc = crc16(np.frombuffer(body, dtype=np.uint8), poly=0x1021, init=0xFFFF, refin=False, refout=False).to_bytes(2, 'big')
        frame = body + crc
        frames.append(frame)
    bitstreams = []
    for fr in frames:
        bits = _bytes_to_bits_be(np.frombuffer(fr, dtype=np.uint8))
        bitstreams.append(bits)
        bitstreams.append(np.zeros(200, dtype=np.uint8))
    bits_all = np.concatenate(bitstreams)
    iq = _bpsk_modulate(bits_all, fs=fs, baud=baud)
    iq = iq + (0.02 * (np.random.randn(*iq.shape) + 1j * np.random.randn(*iq.shape))).astype(np.complex64)
    path = os.path.join(outdir, 'demo.npy')
    np.save(path, iq.astype(np.complex64))
    return path, fs

def _self_tests() -> int:
    import unittest
    class T(unittest.TestCase):
        def test_crc16_ccitt(self):
            msg = b"123456789"
            c = crc16(np.frombuffer(msg, dtype=np.uint8), poly=0x1021, init=0xFFFF, refin=False, refout=False)
            self.assertEqual(c, 0x29B1)
        def test_length_hypothesis(self):
            frames = []
            for pl in [3, 5, 7, 9]:
                header = bytes([0xAB, 0xCD])
                length = bytes([pl])
                payload = bytes(range(pl))
                crc = bytes([0, 0])
                raw = header + length + payload + crc
                frames.append(Frame(offset=0, raw_bytes=np.frombuffer(raw, dtype=np.uint8)))
            hyps = length_hypotheses(frames, max_search=4)
            self.assertTrue(len(hyps) > 0)
            best = hyps[0]
            self.assertEqual(best["offset"], 2)
            self.assertEqual(best["width"], 1)
            self.assertGreater(best["hit_rate"], 0.9)
        def test_checksum_hypothesis_crc16(self):
            frames = []
            for pl in [4, 6, 8]:
                header = bytes([0xAA, 0x55])
                payload = bytes(range(pl))
                body = header + bytes([pl]) + payload
                c = crc16(np.frombuffer(body, dtype=np.uint8), poly=0x1021, init=0xFFFF, refin=False, refout=False)
                raw = body + c.to_bytes(2, 'big')
                frames.append(Frame(offset=0, raw_bytes=np.frombuffer(raw, dtype=np.uint8)))
            hyps = checksum_hypotheses(frames)
            self.assertTrue(len(hyps) > 0)
            top = hyps[0]
            self.assertTrue(str(top["type"]).startswith("crc16_"))
            self.assertEqual(top["tail"], 2)
            self.assertAlmostEqual(top["hit_rate"], 1.0, places=6)
        def test_demo_pipeline(self):
            outdir = "_out_demo_test"
            path, fs = generate_demo_capture(outdir, fs=400_000.0, baud=2_000.0, n_frames=3)
            run(path, fs, outdir, baud_min=500, baud_max=5000, min_burst_ms=1.0)
            self.assertTrue(os.path.exists(os.path.join(outdir, 'grammar_guess.json')))
            with open(os.path.join(outdir, 'grammar_guess.json'), 'r') as f:
                gg = json.load(f)
            self.assertIn('frame_lengths', gg)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(T)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description='Neuro‑Symbolic Protocol Autopsy — Day‑1 Starter',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=True,
    )
    ap.add_argument('--iq', help='Path to I/Q: .npy (complex64), .c8 (int8 interleaved), or .wav stereo')
    ap.add_argument('--fs', type=float, help='Sample rate (Hz) — required if --iq is used')
    ap.add_argument('--out', default='out', help='Output directory')
    ap.add_argument('--baud-min', type=float, default=100.0)
    ap.add_argument('--baud-max', type=float, default=10000.0)
    ap.add_argument('--min-burst-ms', type=float, default=1.0)
    ap.add_argument('--demo', action='store_true', help='Run on a built‑in synthetic BPSK capture')
    ap.add_argument('--demo-fs', type=float, default=1_000_000.0, help='Demo samplerate (Hz)')
    ap.add_argument('--demo-baud', type=float, default=2_000.0, help='Demo baud (sym/s)')
    ap.add_argument('--demo-frames', type=int, default=6, help='Number of frames in demo')
    ap.add_argument('--self-test', action='store_true', help='Run unit tests and exit')
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if len(raw_argv) == 0:
        args = ap.parse_args(['--demo'])
    else:
        try:
            args, unknown = ap.parse_known_args(raw_argv)
            if unknown:
                print(f"[warn] Ignoring unknown args: {unknown}")
        except SystemExit:
            args = ap.parse_args(['--demo'])
    if args.self_test:
        return _self_tests()
    os.makedirs(args.out, exist_ok=True)
    if args.demo:
        demo_path, demo_fs = generate_demo_capture(args.out, fs=args.demo_fs, baud=args.demo_baud, n_frames=args.demo_frames)
        run(demo_path, demo_fs, args.out, args.baud_min, args.baud_max, args.min_burst_ms)
        return 0
    if not args.iq or not args.fs:
        print("[error] Either provide --demo OR provide both --iq and --fs. Example:\n  python nsrf_autopsy_day1_starter.py --iq sample.npy --fs 2e6 --out out\n  python nsrf_autopsy_day1_starter.py --demo")
        return 2
    run(args.iq, args.fs, args.out, args.baud_min, args.baud_max, args.min_burst_ms)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
