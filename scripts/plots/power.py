import math

import altair as alt
import numpy as np
import polars as pl

import dysonsphere as ds

rng = np.random.default_rng(42)

# Pendulum period: T = 2π√(L/g)  →  T is linear in √L.
# On a sqrt x-axis all three bodies appear as straight parallel lines.
BODIES = ["Earth", "Mars", "Moon"]
G = {"Earth": 9.81, "Mars": 3.72, "Moon": 1.62}

LENGTHS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
N_REPS = 10

rows = []
for body in BODIES:
    g = G[body]
    for L in LENGTHS:
        T_true = 2 * math.pi * math.sqrt(L / g)
        for _ in range(N_REPS):
            rows.append(
                {
                    "body": body,
                    "length": float(L),
                    "period": float(T_true * rng.lognormal(0, 0.03)),
                }
            )

df = pl.DataFrame(rows)

L_fit = np.linspace(0.25, 4.0, 100)
fit_rows = []
for body in BODIES:
    for L, T in zip(L_fit, 2 * math.pi * np.sqrt(L_fit / G[body])):
        fit_rows.append({"body": body, "length": float(L), "period": float(T)})
df_fit = pl.DataFrame(fit_rows)

ds.theme(chartWidth=200)

# Major ticks at L = 0.25, 1.0, 2.25, 4.0 → √L = 0.5, 1.0, 1.5, 2.0 (equal spacing)
major_values = [0.25, 1.0, 2.25, 4.0]
x_scale = alt.Scale(type="pow", exponent=0.5, domain=[0.25, 4.0])
x_enc = alt.X(
    "length:Q",
    title="Pendulum length (m, √ scale)",
    scale=x_scale,
    axis=alt.Axis(values=major_values),
)
color_enc = alt.Color("body:N", sort=BODIES, title=None)

points = alt.Chart(df).mark_point().encode(x=x_enc, y=alt.Y("period:Q", title="Period (s)"), color=color_enc)

trend = alt.Chart(df_fit).mark_line().encode(x=alt.X("length:Q", scale=x_scale), y=alt.Y("period:Q"), color=color_enc)

chart = points + trend
chart = ds.add_pow_ticks(chart, df, "length", axis="x", exponent=0.5, majorValues=major_values)

ds.save(chart, "power")
print("saved power")
