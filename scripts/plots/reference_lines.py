"""
Demo of add_rule() reference line helper.

Left panel: strip chart with horizontal lines marking a reference range.
Right panel: time series with a horizontal baseline and a labeled vertical
             line marking an intervention point.
"""

import altair as alt
import numpy as np
import polars as pl

import dysonsphere as ds

rng = np.random.default_rng(42)

GROUPS = ["A", "B", "C", "D"]
palette = ds.palette("blues2", n=4)

# ── Left: strip chart with reference range ────────────────────────────────────
n = 20
df_strip = pl.DataFrame(
    {
        "group": sum([[g] * n for g in GROUPS], []),
        "value": np.concatenate([rng.normal(loc, 0.8, n) for loc in [5.5, 4.8, 6.2, 5.1]]),
    }
)

ds.theme(palette="blues2", chartWidth=120, chartHeight=110)
strip = ds.mark_strip(df_strip, "group", "value", GROUPS, yTitle="Measurement")
left = (
    strip
    + ds.add_rule(4.0, label="Lower limit", labelPosition="bottom")
    + ds.add_rule(7.0, label="Upper limit", labelAlign="right")
).properties(title="add_rule(axis='y')")

# ── Right: time series with baseline + intervention ───────────────────────────
t = np.linspace(0, 20, 60)
SERIES = ["Series 1", "Series 2"]
df_time = pl.DataFrame(
    {
        "time": np.tile(t, 2),
        "value": np.concatenate(
            [
                np.sin(t * 0.5) * 2 + rng.normal(0, 0.15, 60),
                np.cos(t * 0.35) * 1.5 + rng.normal(0, 0.15, 60),
            ]
        ),
        "series": SERIES[0:1] * 60 + SERIES[1:2] * 60,
    }
)

ds.theme(palette="blues2", chartWidth=120, chartHeight=100)
lines = (
    alt.Chart(df_time)
    .mark_line()
    .encode(
        x=alt.X("time:Q", title=None),
        y=alt.Y("value:Q", title=None),
        color=alt.Color(
            "series:N",
            sort=SERIES,
            title=None,
            scale=alt.Scale(range=[ds.palette("blues2")[2], ds.palette("blues2")[7]]),
        ),
    )
)
right = (
    lines
    + ds.add_rule(
        10,
        axis="x",
        label="Intervention",
        labelPosition="right",
        labelAlign="bottom",
    )
).properties(title="add_rule(axis='x')")

chart = alt.hconcat(left, right)
ds.save(chart, "reference_lines")
print("saved reference_lines")
