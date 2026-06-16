import numpy as np
import polars as pl

import theme

rng = np.random.default_rng(42)

CATEGORIES = ["Control", "Drug A", "Drug B", "Drug C", "Drug D", "Drug E"]

df = pl.DataFrame(
    {
        "group": (
            ["Control"] * 200
            + ["Drug A"] * 200
            + ["Drug B"] * 200
            + ["Drug C"] * 200
            + ["Drug D"] * 200
            + ["Drug E"] * 200
        ),
        "value": np.concatenate(
            [
                rng.normal(10, 2, 200),
                rng.normal(14, 2, 200),
                rng.normal(11, 2, 200),
                rng.normal(13, 2, 200),
                rng.normal(9, 2, 200),
                rng.normal(10, 2, 200),
            ]
        ),
    }
)

theme.options(chartWidth=150)
palette = theme.palette_range("lagoon_4_oklab", n=len(CATEGORIES))

chart = theme.mark_violin(df, "group", "value", CATEGORIES, labelAngle=-45, palette=palette)

theme.save(chart, "violin")
print("saved violin")
