import altair as alt
import numpy as np
import polars as pl

import theme

rng = np.random.default_rng(42)

VARIABLES = ["Gene A", "Gene B", "Gene C", "Gene D", "Gene E", "Gene F"]
n = len(VARIABLES)

cov = rng.uniform(-0.6, 0.6, (n, n))
cov = (cov + cov.T) / 2
np.fill_diagonal(cov, 1.0)

rows = []
for i, v1 in enumerate(VARIABLES):
    for j, v2 in enumerate(VARIABLES):
        rows.append({"var1": v1, "var2": v2, "correlation": float(cov[i, j])})

df = pl.DataFrame(rows)

palette = theme.palette_range("lagoon_4_oklab")

theme.options(chartWidth=150, chartHeight=150)

axis_x = alt.Axis(
    labelAngle=-45,
    labelAlign="right",
    domain=False,
    ticks=False,
    labelPadding=2,
)
axis_y = alt.Axis(
    domain=False,
    ticks=False,
    labelPadding=2,
)

chart = (
    alt.Chart(df)
    .mark_rect()
    .encode(
        x=alt.X(
            "var1:N",
            sort=VARIABLES,
            title=None,
            axis=axis_x,
            scale=alt.Scale(paddingInner=0, paddingOuter=0),
        ),
        y=alt.Y(
            "var2:N",
            sort=VARIABLES[::-1],
            title=None,
            axis=axis_y,
            scale=alt.Scale(paddingInner=0, paddingOuter=0),
        ),
        color=alt.Color(
            "correlation:Q",
            scale=alt.Scale(range=palette, domain=[-1, 1]),
            title=None,
        ),
    )
)

theme.save(chart, "heatmap")
print("saved heatmap")
