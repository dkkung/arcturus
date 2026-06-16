"""
Oklab palette exploration.

Compares palette design in CIELAB vs Oklab for the same hue families.
Oklab (Ottosson 2020) has better hue linearity than CIELAB, especially
in the blue region.  The perceptual distance metric here is Oklab ΔE
(Euclidean distance in Oklab space).
"""

import math
import altair as alt
import polars as pl
import numpy as np
import theme
from theme.palettes import colors as stored

W = 65


# ── Oklab conversion ───────────────────────────────────────────────────────
# Reference: https://bottosson.github.io/posts/oklab/
# sRGB → linear sRGB → Oklab (and back)

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _gamma(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

def hex_to_oklab(hx):
    h = hx.lstrip("#")
    r, g, b = [_lin(int(h[i:i+2], 16) / 255) for i in (0, 2, 4)]
    # linear sRGB → Oklab LMS
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l_, m_, s_ = l**(1/3), m**(1/3), s**(1/3)
    L =  0.2104542553*l_ + 0.7936177850*m_ - 0.0040720468*s_
    a =  1.9779984951*l_ - 2.4285922050*m_ + 0.4505937099*s_
    b_ = 0.0259040371*l_ + 0.7827717662*m_ - 0.8086757660*s_
    return L, a, b_

def oklab_to_hex(L, a, b):
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l, m, s = l_**3, m_**3, s_**3
    r =  4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    b_ = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    def clamp(v): return max(0.0, min(1.0, v))
    return "#{:02X}{:02X}{:02X}".format(
        round(clamp(_gamma(r))*255),
        round(clamp(_gamma(g))*255),
        round(clamp(_gamma(b_))*255),
    )

def _in_gamut_oklab(L, a, b):
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l, m, s = l_**3, m_**3, s_**3
    r =  4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    bv = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return all(0 <= v <= 1 for v in [r, g, bv])

def max_chroma_oklab(L, h_rad):
    lo, hi = 0.0, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        if _in_gamut_oklab(L, mid*math.cos(h_rad), mid*math.sin(h_rad)):
            lo = mid
        else:
            hi = mid
    return lo

def delta_e_oklab(lab1, lab2):
    return math.sqrt(sum((a-b)**2 for a,b in zip(lab1, lab2)))


# ── Palette builders in Oklab ──────────────────────────────────────────────

def make_oklab_seq(key, frac=0.65, n_out=9, n_seg=200):
    """
    Port of sat2 logic into Oklab:
    saturate each base stop to frac*C_max, then equal-arc-length resample.
    """
    hexes = stored[key]
    labs  = [hex_to_oklab(h) for h in hexes]

    max_c = max(math.sqrt(a**2+b**2) for _,a,b in labs)
    if max_c < 0.01:  # neutral (greys)
        return list(hexes)

    sat_labs = []
    for L, a, b in labs:
        C = math.sqrt(a**2 + b**2)
        if C < 0.005:
            sat_labs.append((L, a, b))
        else:
            h = math.atan2(b, a)
            C_new = frac * max_chroma_oklab(L, h)
            sat_labs.append((L, C_new*math.cos(h), C_new*math.sin(h)))

    # Dense piecewise-linear path in Oklab
    Ld, ad, bd = [], [], []
    for i in range(len(sat_labs) - 1):
        L0, a0, b0 = sat_labs[i]
        L1, a1, b1 = sat_labs[i+1]
        for j in range(n_seg):
            t = j / n_seg
            Ld.append(L0 + t*(L1-L0))
            ad.append(a0 + t*(a1-a0))
            bd.append(b0 + t*(b1-b0))
    Ld.append(sat_labs[-1][0]); ad.append(sat_labs[-1][1]); bd.append(sat_labs[-1][2])

    arc = [0.0]
    for i in range(1, len(Ld)):
        dL=Ld[i]-Ld[i-1]; da=ad[i]-ad[i-1]; db=bd[i]-bd[i-1]
        arc.append(arc[-1] + math.sqrt(dL**2+da**2+db**2))
    total = arc[-1]

    result, j = [], 0
    for k in range(n_out):
        target = k * total / (n_out - 1)
        while j < len(Ld)-1 and arc[j+1] <= target:
            j += 1
        if j == 0 or arc[j] <= target:
            result.append(oklab_to_hex(Ld[j], ad[j], bd[j]))
        else:
            t_i = (target - arc[j-1]) / (arc[j] - arc[j-1])
            L = Ld[j-1] + t_i*(Ld[j]-Ld[j-1])
            a = ad[j-1] + t_i*(ad[j]-ad[j-1])
            b = bd[j-1] + t_i*(bd[j]-bd[j-1])
            result.append(oklab_to_hex(L, a, b))
    return result


def make_oklab_diverg(key, frac=0.65, n=9, n_dense=1000):
    """
    Diverging: arm-based approach in Oklab.
    C(t) = frac * min_gamut_both_arms(L) * (1 - t), equal arc-length sampling.
    """
    hexes = stored[key]
    labs  = [hex_to_oklab(h) for h in hexes]
    center = n // 2

    h1 = math.atan2(labs[0][2], labs[0][1])
    h2 = math.atan2(labs[-1][2], labs[-1][1])
    L_dark = labs[0][0]
    L_ctr  = labs[center][0]

    L_arr = [L_dark + (L_ctr - L_dark) * i / (n_dense-1) for i in range(n_dense)]
    t_arr = [i / (n_dense-1) for i in range(n_dense)]
    C_arr = [frac * min(max_chroma_oklab(L, h1), max_chroma_oklab(L, h2)) * (1-t)
             for L, t in zip(L_arr, t_arr)]

    arc = [0.0]
    for i in range(1, n_dense):
        dL = L_arr[i]-L_arr[i-1]; dC = C_arr[i]-C_arr[i-1]
        arc.append(arc[-1] + math.sqrt(dL**2+dC**2))
    total = arc[-1]
    half = n // 2

    def sample_arm(h_rad):
        result, j = [], 0
        for k in range(half):
            target = k * total / half
            while j < n_dense-1 and arc[j+1] <= target:
                j += 1
            if j == 0:
                result.append(oklab_to_hex(L_arr[0], C_arr[0]*math.cos(h_rad), C_arr[0]*math.sin(h_rad)))
            else:
                t_i = (target - arc[j-1]) / (arc[j] - arc[j-1])
                L = L_arr[j-1] + t_i*(L_arr[j]-L_arr[j-1])
                C = C_arr[j-1] + t_i*(C_arr[j]-C_arr[j-1])
                result.append(oklab_to_hex(L, C*math.cos(h_rad), C*math.sin(h_rad)))
        return result

    arm1 = sample_arm(h1)
    arm2 = sample_arm(h2)
    center_hex = oklab_to_hex(L_ctr, 0.0, 0.0)
    return arm1 + [center_hex] + arm2[::-1]


# ── Diagnostics ────────────────────────────────────────────────────────────

def report(label, hexes, metric="oklab"):
    if metric == "oklab":
        labs = [hex_to_oklab(h) for h in hexes]
    else:
        from examples.palette_test import hex_to_lab  # fallback
        labs = [hex_to_lab(h) for h in hexes]
    steps = [delta_e_oklab(labs[i], labs[i+1]) for i in range(len(labs)-1)]
    mad = sum(abs(s - sum(steps)/len(steps)) for s in steps) / len(steps)
    print(f"  {label:<28}  ΔE steps: {[round(s,3) for s in steps]}  MAD={mad:.4f}")


# ── Palettes to compare ────────────────────────────────────────────────────

SEQ_KEYS = [
    "blues", "purples", "greens",
    "reds",  "oranges", "GnBu",
    "YlGnBu", "RdPu",
]
DIV_KEYS = [
    "RdBu", "PuGn", "BrTe",
    "GdBu", "MgGn", "YlPu",
]

print("Sequential — Oklab ΔE uniformity:")
oklab_seq = {}
for key in SEQ_KEYS:
    hexes = make_oklab_seq(key)
    oklab_seq[key] = hexes
    report(key + "_oklab", hexes)

print("\nDiverging — Oklab ΔE uniformity:")
oklab_div = {}
for key in DIV_KEYS:
    hexes = make_oklab_diverg(key)
    oklab_div[key] = hexes
    report(key + "_oklab", hexes)

print("\nCIELAB sat2 — Oklab ΔE for comparison:")
for key in SEQ_KEYS:
    sat2_key = key + "_sat2"
    if sat2_key in stored:
        report(sat2_key + " (CIELAB, Oklab ΔE)", stored[sat2_key])


# ── Scatter data ───────────────────────────────────────────────────────────

rng = np.random.default_rng(42)
x = np.linspace(0, 5, 200); y = np.exp(x) + rng.normal(0, 2, 200)
mask = y >= 0; x, y = x[mask], y[mask]
scatter_df = pl.DataFrame({"x": x, "y": y})


# ── Chart helpers ──────────────────────────────────────────────────────────

def swatch(hexes, label=""):
    p = hexes
    df = pl.DataFrame({"i": list(range(len(p))), "c": p})
    return (
        alt.Chart(df)
        .mark_rect(strokeWidth=0)
        .encode(
            x=alt.X("i:O", axis=None, scale=alt.Scale(paddingInner=0, paddingOuter=0)),
            color=alt.Color("c:N", scale=alt.Scale(domain=p, range=p), legend=None),
        )
        .properties(width=W, height=10)
    )

def scatter(hexes):
    p = hexes
    return (
        alt.Chart(scatter_df).mark_point()
        .encode(
            x=alt.X("x:Q", title="x"),
            y=alt.Y("y:Q", axis=None),
            color=alt.Color("y:Q", title=None, scale=alt.Scale(range=p)),
        )
        .properties(width=W, height=W)
    )

def de_chart_overlay(hexes_cielab, hexes_oklab):
    """Both series on the same chart, Y-axis zoomed to actual range."""
    rows = []
    for label, hexes in [("sat2", hexes_cielab), ("oklab", hexes_oklab)]:
        labs  = [hex_to_oklab(h) for h in hexes]
        steps = [delta_e_oklab(labs[i], labs[i+1]) for i in range(len(labs)-1)]
        for i, s in enumerate(steps):
            rows.append({"series": label, "step": i, "dE": round(s, 5)})
    df = pl.DataFrame(rows)
    all_vals = [r["dE"] for r in rows]
    lo = min(all_vals) * 0.85
    hi = max(all_vals) * 1.15
    domain  = ["sat2", "oklab"]
    range_c = ["#999999", "#E45756"]
    return (
        alt.Chart(df, title="ΔE Oklab")
        .mark_line(point=True, strokeWidth=1)
        .encode(
            x=alt.X("step:Q", title=None, axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("dE:Q",   title="ΔE", scale=alt.Scale(domain=[lo, hi])),
            color=alt.Color("series:N",
                            scale=alt.Scale(domain=domain, range=range_c),
                            legend=None),
        )
        .properties(width=W, height=50)
    )

def col(hexes_cielab, hexes_oklab, label):
    return (
        alt.vconcat(
            swatch(hexes_cielab).properties(title=label + " ·sat2"),
            scatter(hexes_cielab),
            swatch(hexes_oklab).properties(title=label + " ·oklab"),
            scatter(hexes_oklab),
            de_chart_overlay(hexes_cielab, hexes_oklab),
            spacing=4,
        )
        .resolve_scale(color="independent")
    )


# ── Compose ────────────────────────────────────────────────────────────────

seq_cols = [
    col(stored[k + "_sat2"], oklab_seq[k], k.replace("custom_", ""))
    for k in SEQ_KEYS
]
div_cols = [
    col(stored[k + "_sat2"], oklab_div[k], k.replace("custom_", ""))
    for k in DIV_KEYS
]

chart = alt.vconcat(
    alt.hconcat(*seq_cols, spacing=10, title="Sequential").resolve_scale(color="independent"),
    alt.hconcat(*div_cols, spacing=10, title="Diverging").resolve_scale(color="independent"),
    spacing=20,
).resolve_scale(color="independent")

theme.options(chartWidth=W, chartHeight=W)
theme.save(chart, "oklab_test", ppi=150)
print("\nsaved oklab_test")
