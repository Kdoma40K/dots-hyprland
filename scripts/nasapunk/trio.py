"""Prototype of the NASA-punk wallpaper -> theme pipeline.

For each wallpaper: pick light/dark mode from the bar area, cluster colors in
OKLab, choose SIGNAL (boldest hue), TRACE (second hue, calmer) and TINT (the
wallpaper's average hue at very low chroma), then clamp each into a safe
lightness/chroma window for the chosen mode.
"""
import json
import math
import sys

import numpy as np
from PIL import Image

FALLBACK_SIGNAL = (0.5523, 0.2056, 27.0)  # Nothing-style red, OKLCh

LIMITS = {
    "dark": {"signal": ((0.64, 0.74), (0.09, 0.16)), "trace": ((0.66, 0.80), (0.03, 0.08)), "tintL": 0.17, "tintC": 0.012},
    "light": {"signal": ((0.50, 0.60), (0.09, 0.17)), "trace": ((0.44, 0.58), (0.03, 0.08)), "tintL": 0.95, "tintC": 0.010},
}


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055)


def rgb_to_oklab(rgb):
    lin = srgb_to_linear(rgb)
    m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    lms = np.cbrt(lin @ m1.T)
    m2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    return lms @ m2.T


def oklab_to_rgb(lab):
    m2i = np.array([[1, 0.3963377774, 0.2158037573],
                    [1, -0.1055613458, -0.0638541728],
                    [1, -0.0894841775, -1.2914855480]])
    lms = (np.asarray(lab) @ m2i.T) ** 3
    m1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                    [-1.2684380046, 2.6097574011, -0.3413193965],
                    [-0.0041960863, -0.7034186147, 1.7076147010]])
    return linear_to_srgb(lms @ m1i.T)


def lch_to_hex(L, C, h):
    while True:
        a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
        rgb = oklab_to_rgb(np.array([L, a, b]))
        if np.all(rgb >= -0.001) and np.all(rgb <= 1.001) or C < 0.002:
            break
        C -= 0.005  # gamut-map by dropping chroma
    rgb = np.clip(rgb, 0, 1)
    return "#" + "".join(f"{int(round(v * 255)):02x}" for v in rgb)


def kmeans(x, k=8, iters=20, seed=1):
    rng = np.random.default_rng(seed)
    cent = x[rng.choice(len(x), k, replace=False)]
    for _ in range(iters):
        d = ((x[:, None, :] - cent[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for i in range(k):
            pts = x[lab == i]
            if len(pts):
                cent[i] = pts.mean(0)
    w = np.bincount(lab, minlength=k) / len(x)
    return cent, w


def hue_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def analyse(path):
    img = Image.open(path).convert("RGB")
    img.thumbnail((240, 240))
    px = np.asarray(img).astype(float) / 255.0
    h = px.shape[0]
    lab_all = rgb_to_oklab(px.reshape(-1, 3))
    lab_top = rgb_to_oklab(px[: max(1, int(h * 0.12))].reshape(-1, 3))
    mode = "light" if lab_top[:, 0].mean() > 0.66 else "dark"
    lim = LIMITS[mode]

    cent, w = kmeans(lab_all)
    clusters = []
    for (L, a, b), wt in zip(cent, w):
        C = math.hypot(a, b)
        hue = math.degrees(math.atan2(b, a)) % 360
        clusters.append({"L": L, "C": C, "h": hue, "w": float(wt)})

    # Hue peaks from individual vivid pixels (cluster means wash out small, loud areas).
    Ls = lab_all[:, 0]
    Cs = np.hypot(lab_all[:, 1], lab_all[:, 2])
    Hs = np.degrees(np.arctan2(lab_all[:, 2], lab_all[:, 1])) % 360
    vivid = Cs >= 0.07
    peaks = []
    if vivid.mean() >= 0.005:
        hist = np.zeros(36)
        np.add.at(hist, (Hs[vivid] // 10).astype(int) % 36, Cs[vivid])
        order = np.argsort(hist)[::-1]
        for b in order:
            if hist[b] <= 0:
                break
            centre = b * 10 + 5
            if any(hue_diff(centre, p["h"]) < 40 for p in peaks):
                continue
            band = vivid & (np.array([hue_diff(x, centre) for x in Hs]) <= 15)
            peaks.append({"h": float(np.degrees(np.arctan2(np.sin(np.radians(Hs[band])).mean(), np.cos(np.radians(Hs[band])).mean())) % 360),
                          "C": float(np.percentile(Cs[band], 80)), "L": float(np.median(Ls[band])), "mass": float(hist[b])})
            if len(peaks) == 2:
                break

    (sl, sc) = lim["signal"]
    if peaks:
        p = peaks[0]
        signal = lch_to_hex(min(max(p["L"], sl[0]), sl[1]), min(max(p["C"], sc[0]), sc[1]), p["h"])
        sig_h = p["h"]
        source = "wallpaper"
    else:
        signal = "#d71921"  # pinned fallback bypasses the clamp
        sig_h = FALLBACK_SIGNAL[2]
        source = "fallback red"

    (tl, tc) = lim["trace"]
    if len(peaks) == 2 and peaks[1]["mass"] >= 0.12 * peaks[0]["mass"]:
        p = peaks[1]
        trace = lch_to_hex(min(max(p["L"], tl[0]), tl[1]), min(max(p["C"], tc[0]), tc[1]), p["h"])
        trace_src = "second hue"
    elif any(c["w"] >= 0.05 and c["C"] >= 0.025 and hue_diff(c["h"], sig_h) >= 40 for c in clusters):
        c = max((c for c in clusters if c["w"] >= 0.05 and c["C"] >= 0.025 and hue_diff(c["h"], sig_h) >= 40), key=lambda c: c["w"])
        trace = lch_to_hex(min(max(c["L"], tl[0]), tl[1]), min(max(c["C"], tc[0]), tc[1]), c["h"])
        trace_src = "muted field"
    else:
        trace = lch_to_hex((tl[0] + tl[1]) / 2, tc[0], sig_h)
        trace_src = "calm signal"

    mean_a, mean_b = lab_all[:, 1].mean(), lab_all[:, 2].mean()
    avg_h = math.degrees(math.atan2(mean_b, mean_a)) % 360
    tint = lch_to_hex(lim["tintL"], lim["tintC"], avg_h)
    tint2 = lch_to_hex(lim["tintL"] + (0.05 if mode == "dark" else -0.04), lim["tintC"], avg_h)

    return {"mode": mode, "signal": signal, "signal_src": source, "trace": trace, "trace_src": trace_src,
            "tint": tint, "tint2": tint2, "topL": round(float(lab_top[:, 0].mean()), 3)}


if __name__ == "__main__":
    out = {p: analyse(p) for p in sys.argv[1:]}
    print(json.dumps(out, indent=1))
