from pathlib import Path

import altair as alt
import polars as pl

import dysonsphere as ds

CATEGORIES = ["Kinases", "Transcription factors", "GPCRs", "Channels", "Other"]
COUNTS = [342, 267, 189, 143, 401]

df = pl.DataFrame({"category": CATEGORIES, "count": COUNTS})

palette = ds.palette("blues2", n=len(CATEGORIES), start=0)

ds.theme(chartWidth=100, chartHeight=100, legend=True, ticks=False, closed=False)

chart = (
    alt.Chart(df)
    .mark_arc()
    .encode(
        theta=alt.Theta("count:Q"),
        color=alt.Color(
            "category:N",
            sort=CATEGORIES,
            title=None,
            scale=alt.Scale(domain=CATEGORIES, range=palette),
        ),
        tooltip=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("count:Q", title="Proteins", format=","),
        ],
    )
)

out = str(Path(__file__).parent / "arc")
ds.save(chart, out)
print(f"saved {out}")
