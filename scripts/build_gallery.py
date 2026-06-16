"""
Interactive HTML gallery of all custom palettes.

Usage (from project root):
    python -m theme.gallery
    python theme/gallery.py

Output: gallery.html at the project root.
"""

import math
from pathlib import Path

import altair as alt
import numpy as np
import polars as pl

from .palettes import colors
from .transforms import add_beeswarm_offsets

W = 100  # base chart width / height (px)

# ── Oklab helpers (inlined — no dependency on examples/) ───────────────────


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _hex_to_oklab(hx):
    h = hx.lstrip("#")
    r, g, b = [_lin(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4)]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _de_steps(key):
    hexes = colors[key]
    labs = [_hex_to_oklab(h) for h in hexes]
    return [
        math.sqrt(sum((a - b) ** 2 for a, b in zip(labs[i], labs[i + 1])))
        for i in range(len(labs) - 1)
    ]


def _mad_pct(steps):
    mean = sum(steps) / len(steps)
    mad = sum(abs(s - mean) for s in steps) / len(steps)
    return round(mad / mean * 100, 1)


# ── Palette groups ──────────────────────────────────────────────────────────

GROUPS = [
    ("Sequential — Single-hue analogs", ["blues", "greens", "purples", "lavenders", "byzantiums", "greys", "reds", "rose", "oranges", "browns", "yellows", "cyans", "magentas"]),
    ("Sequential — Multi-hue analogs", ["ember", "dusk", "moss", "GnBu", "YlGnBu", "candy"]),
    ("Sequential — Showcase multi-hue", ["lagoon", "bluestgrotto", "bluestgrotto2", "bluestgrotto3", "bluestgrotto4", "bluergrotto", "bluergrotto2", "bluergrotto3", "bluergrotto4", "bluegrotto", "bluegrotto2", "bluegrotto3", "bluegrotto4"]),
    ("Diverging", ["RdBu", "RdBu_sat", "PuGn", "PuGn_sat", "BrTe", "BrTe_sat", "GdBu", "GdBu_sat", "MgGn", "MgGn_sat", "YlPu", "YlPu_sat"]),
]
# Keys that are already final variants (no base+suffix convention)
LITERAL_KEYS = []

VARIANTS = [("", "")]

# ── Synthetic data ──────────────────────────────────────────────────────────

_rng = np.random.default_rng(42)

# Scatter: exponential curve with noise (200 pts)
_sx = np.linspace(0, 5, 200)
_sy = np.exp(_sx) + _rng.normal(0, 2, 200)
_smask = _sy >= 0
_scatter_df = pl.DataFrame({"x": _sx[_smask].tolist(), "y": _sy[_smask].tolist()})

# Heatmap: denser grid (500 pts) for fuller bin coverage
_hx = np.linspace(0, 5, 500)
_hy = np.exp(_hx) + _rng.normal(0, 2, 500)
_hmask = _hy >= 0
_heat_df = pl.DataFrame({"x": _hx[_hmask].tolist(), "y": _hy[_hmask].tolist()})

# Area chart: 4 stacked proportions over time (mirrors examples/area_chart.py)
_AREA_GROUPS = ["Type A", "Type B", "Type C", "Type D"]
_AREA_BASES = [0.4, 0.3, 0.2, 0.1]
_area_rows = []
for _t in np.linspace(0, 24, 100):
    for _grp, _base in zip(_AREA_GROUPS, _AREA_BASES):
        _area_rows.append({"time": float(_t), "group": _grp,
                           "value": max(0.0, _base + _rng.normal(0, 0.02))})
_area_df = pl.DataFrame(_area_rows)

# Boxplot: normally distributed groups like boxplot.py, 200 pts per bin
_CATEGORIES = ["0–1", "1–2", "2–3", "3–4", "4–5"]
_box_raw = pl.DataFrame(
    {
        "bin": _CATEGORIES * 200,
        "value": np.concatenate(
            [
                _rng.normal(1.0, 0.4, 200),
                _rng.normal(3.5, 0.8, 200),
                _rng.normal(8.0, 1.5, 200),
                _rng.normal(18.0, 3.0, 200),
                _rng.normal(38.0, 6.0, 200),
            ]
        ).tolist(),
    }
)
_N_BINS = len(_CATEGORIES)
_BIN_LABELS = _CATEGORIES
_box_df = add_beeswarm_offsets(_box_raw, y_col="value", group_by=["bin"], step=2)

# Pre-compute viridis reference steps
_VIR_STEPS = _de_steps("mpl_viridis")
_VIR_MAD = _mad_pct(_VIR_STEPS)

# ── Chart builders ──────────────────────────────────────────────────────────


def _swatch(key, label):
    p = colors[key]
    n = len(p)
    df = pl.DataFrame(
        {
            "x1": list(range(n)),
            "x2": list(range(1, n + 1)),
            "c": p,
        }
    )
    return (
        alt.Chart(df, title=alt.TitleParams(label, fontSize=11, fontWeight="normal"))
        .mark_rect(strokeWidth=0)
        .encode(
            x=alt.X("x1:Q", axis=None, scale=alt.Scale(domain=[0, n], nice=False)),
            x2=alt.X2("x2:Q"),
            color=alt.Color("c:N", scale=None, legend=None),
            tooltip=alt.Tooltip("c:N", title="hex"),
        )
        .properties(width=W, height=14)
    )


def _scatter(key):
    p = colors[key]
    return (
        alt.Chart(_scatter_df)
        .mark_point(size=18, opacity=0.85, stroke="black")
        .encode(
            x=alt.X("x:Q", title=None, axis=alt.Axis(tickCount=4, labelFontSize=8, grid=False)),
            y=alt.Y("y:Q", title=None, axis=alt.Axis(tickCount=4, labelFontSize=8, grid=False)),
            color=alt.Color("y:Q", scale=alt.Scale(range=p), legend=None),
            tooltip=[
                alt.Tooltip("x:Q", format=".2f"),
                alt.Tooltip("y:Q", format=".1f"),
            ],
        )
        .properties(width=W, height=W)
    )


def _boxplot(key):
    p = colors[key]
    n = len(p)
    # Map each of the N bins to a colour from the palette
    bin_colors = [p[round(i * (n - 1) / (_N_BINS - 1))] for i in range(_N_BINS)]
    x_enc = alt.X(
        "bin:N", sort=_BIN_LABELS, title=None, axis=alt.Axis(labels=False, ticks=False, grid=False)
    )
    y_enc = alt.Y("value:Q", title=None, axis=alt.Axis(tickCount=4, labelFontSize=8, grid=False))
    color_enc = alt.Color(
        "bin:N",
        sort=_BIN_LABELS,
        legend=None,
        scale=alt.Scale(domain=_BIN_LABELS, range=bin_colors),
    )

    boxes = alt.Chart(_box_df).mark_boxplot(size=14).encode(x=x_enc, y=y_enc, color=color_enc)
    pts = (
        alt.Chart(_box_df)
        .mark_circle(size=5)
        .encode(
            x=x_enc,
            xOffset=alt.XOffset("beeswarm_x:Q"),
            y=y_enc,
            color=color_enc,
        )
    )
    return (pts + boxes).properties(width=W, height=W).resolve_scale(color="independent")


def _heatmap(key):
    p = colors[key]
    return (
        alt.Chart(_heat_df)
        .mark_rect(stroke="white")
        .encode(
            x=alt.X(
                "x:Q",
                bin=alt.Bin(maxbins=12),
                title=None,
                axis=alt.Axis(tickCount=4, labelFontSize=8, grid=False),
            ),
            y=alt.Y(
                "y:Q",
                bin=alt.Bin(maxbins=12),
                title=None,
                axis=alt.Axis(tickCount=4, labelFontSize=8, grid=False),
            ),
            color=alt.Color("count()", scale=alt.Scale(range=p), legend=None),
            tooltip=alt.Tooltip("count()", title="count"),
        )
        .properties(width=W, height=W)
    )


def _area(key):
    p = colors[key]
    n = len(p)
    # Pick 4 evenly-spaced stops from the palette
    palette = [p[round(i * (n - 1) / (len(_AREA_GROUPS) - 1))] for i in range(len(_AREA_GROUPS))]
    return (
        alt.Chart(_area_df)
        .mark_area()
        .encode(
            x=alt.X("time:Q", title=None, axis=alt.Axis(tickCount=4, labelFontSize=8, grid=False)),
            y=alt.Y(
                "value:Q",
                title=None,
                stack="normalize",
                scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(tickCount=3, labelFontSize=8, grid=False),
            ),
            color=alt.Color(
                "group:N",
                sort=_AREA_GROUPS,
                scale=alt.Scale(range=palette),
                legend=None,
            ),
            order=alt.Order("group:N", sort="descending"),
        )
        .properties(width=W, height=W)
    )


def _de_sparkline(key):
    steps = _de_steps(key)
    mad = _mad_pct(steps)
    mid_hex = colors[key][len(colors[key]) // 2]

    pal_rows = [{"step": i, "dE": round(s, 5)} for i, s in enumerate(steps)]
    vir_rows = [{"step": i, "dE": round(s, 5)} for i, s in enumerate(_VIR_STEPS)]
    pal_df = pl.DataFrame(pal_rows)
    vir_df = pl.DataFrame(vir_rows)

    all_de = [r["dE"] for r in pal_rows + vir_rows]
    lo, hi = min(all_de) * 0.82, max(all_de) * 1.18

    y_enc = alt.Y(
        "dE:Q",
        title=None,
        scale=alt.Scale(domain=[lo, hi]),
        axis=alt.Axis(tickCount=3, labelFontSize=8),
    )
    x_enc = alt.X(
        "step:Q", title=None, axis=alt.Axis(tickMinStep=1, labels=False, ticks=False, domain=False)
    )

    # Viridis: solid line + points
    vir_line = (
        alt.Chart(vir_df)
        .mark_line(
            point=alt.OverlayMarkDef(size=25, color="#AAAAAA"),
            strokeWidth=1.5,
            color="#AAAAAA",
            opacity=0.85,
        )
        .encode(
            x=x_enc,
            y=y_enc,
            tooltip=[alt.Tooltip("step:Q"), alt.Tooltip("dE:Q", format=".4f", title="viridis ΔE")],
        )
    )
    # Palette: line + points
    pal_line = (
        alt.Chart(pal_df)
        .mark_line(point=alt.OverlayMarkDef(size=30), strokeWidth=1.5, color=mid_hex)
        .encode(
            x=x_enc,
            y=y_enc,
            tooltip=[alt.Tooltip("step:Q"), alt.Tooltip("dE:Q", format=".4f", title="ΔE")],
        )
    )

    return (vir_line + pal_line).properties(
        width=W, height=55, title=alt.TitleParams(f"MAD {mad}%", fontSize=10)
    )


def _colorspace(key):
    """Palette trajectory in Oklab a/b space, each stop colored by its hex."""
    hexes = colors[key]
    labs = [_hex_to_oklab(h) for h in hexes]
    rows = [
        {
            "hex": h,
            "a": round(a, 4),
            "b": round(b, 4),
            "L": round(L, 3),
            "i": i,
            "label": f"#{i} {h}",
        }
        for i, (h, (L, a, b)) in enumerate(zip(hexes, labs))
    ]
    df = pl.DataFrame(rows)
    domain = [r["hex"] for r in rows]

    line = (
        alt.Chart(df)
        .mark_line(color="#dddddd", strokeWidth=1, opacity=0.7)
        .encode(x="a:Q", y="b:Q", order="i:O")
    )
    pts = (
        alt.Chart(df)
        .mark_circle(size=70, strokeWidth=1, stroke="white")
        .encode(
            x=alt.X(
                "a:Q",
                scale=alt.Scale(padding=12),
                axis=alt.Axis(title="a", labelFontSize=8, tickCount=3),
            ),
            y=alt.Y(
                "b:Q",
                scale=alt.Scale(padding=12),
                axis=alt.Axis(title="b", labelFontSize=8, tickCount=3),
            ),
            color=alt.Color("hex:N", scale=alt.Scale(domain=domain, range=domain), legend=None),
            opacity=alt.Opacity(
                "L:Q", scale=alt.Scale(domain=[0.05, 1.0], range=[0.45, 1.0]), legend=None
            ),
            tooltip=[
                alt.Tooltip("label:N", title="stop"),
                alt.Tooltip("L:Q", format=".2f"),
                alt.Tooltip("a:Q", format=".3f"),
                alt.Tooltip("b:Q", format=".3f"),
            ],
        )
    )
    return (
        (line + pts)
        .properties(width=W, height=W, title=alt.TitleParams("Oklab a/b", fontSize=10))
        .resolve_scale(color="independent", opacity="independent")
    )


# ── Row: all charts for one palette key (landscape layout) ─────────────────


def _row(key, label):
    swatch = _swatch(key, label)
    # Swatch spans full row width — stretch it to match the hconcat width
    return alt.vconcat(
        swatch,
        alt.hconcat(
            _scatter(key),
            _boxplot(key),
            _heatmap(key),
            _area(key),
            _de_sparkline(key),
            _colorspace(key),
            spacing=6,
        ).resolve_scale(color="independent", opacity="independent"),
        spacing=2,
    ).resolve_scale(color="independent", opacity="independent")


# ── Compose ─────────────────────────────────────────────────────────────────


def _build_gallery():
    rows = []

    for group_title, base_keys in GROUPS:
        # Group heading row
        heading = (
            alt.Chart(pl.DataFrame({"x": [0]}))
            .mark_text(
                text=group_title,
                align="left",
                baseline="top",
                fontSize=13,
                fontWeight="bold",
                color="#333333",
                dx=2,
            )
            .encode()
            .properties(width=W * 6 + 6 * 5, height=18)
        )
        rows.append(heading)

        for suffix, _vlabel in VARIANTS:
            for bk in base_keys:
                key = bk + suffix
                if key not in colors:
                    continue
                rows.append(_row(key, bk))

    return (
        alt.vconcat(*rows, spacing=12)
        .resolve_scale(color="independent", opacity="independent")
    )


# ── Vega library inlining (so the HTML is self-contained, no CDN required) ───

_VEGA_URLS = [
    "https://cdn.jsdelivr.net/npm/vega@6",
    "https://cdn.jsdelivr.net/npm/vega-lite@6.4.1",
    "https://cdn.jsdelivr.net/npm/vega-embed@7",
]
_CACHE_DIR = Path(__file__).parent / ".vega_cache"


def _fetch_script(url: str) -> str:
    """Fetch a JS library (with on-disk cache so we don't re-download)."""
    import urllib.request, hashlib
    _CACHE_DIR.mkdir(exist_ok=True)
    cache_file = _CACHE_DIR / hashlib.md5(url.encode()).hexdigest()
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode("utf-8")
    cache_file.write_text(body, encoding="utf-8")
    return body


def _inline_vega_scripts(html_path: Path) -> None:
    """Replace CDN <script src=…> tags with inline <script>…</script> blocks."""
    html = html_path.read_text(encoding="utf-8")
    for url in _VEGA_URLS:
        js = _fetch_script(url)
        # Tag form produced by Altair is: <script type="text/javascript" src="URL"></script>
        tag = f'<script type="text/javascript" src="{url}"></script>'
        inline = f'<script type="text/javascript">{js}</script>'
        if tag not in html:
            print(f"  warning: expected script tag not found: {url}")
            continue
        html = html.replace(tag, inline)
    html_path.write_text(html, encoding="utf-8")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import theme as _theme

    _theme.options(chartWidth=W, chartHeight=W)

    gallery = _build_gallery()

    out = Path(__file__).parent.parent / "gallery.html"
    gallery.save(str(out))
    print(f"saved {out}")

    _inline_vega_scripts(out)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"inlined vega libraries → file is now {size_mb:.1f} MB (self-contained)")
