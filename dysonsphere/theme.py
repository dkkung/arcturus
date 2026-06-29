import os
import tomllib
from pathlib import Path
from typing import Any

import altair as alt

from .palettes import colors

_BUILTIN_DEFAULTS: dict[str, Any] = {
    "axisOffset": None,
    "axisWidth": 0.25,
    "bandPadding": 0.1,
    "chartFill": None,
    "chartHeight": 100,
    "chartWidth": 100,
    "closed": None,
    "darkmode": False,
    "dashedGrid": False,
    "dashedLine": False,
    "dashedRule": True,
    "dashedWidth": [2, 2],
    "font": "HelveticaNeue",
    "fontSize": 7,
    "fontStyle": "normal",
    "fontWeight": 400,
    "grid": False,
    "gridColor": colors["greys"][0],
    "legend": True,
    "legendOffset": None,
    "legendStroke": False,
    "markFill": "black",
    "markFillOpacity": 1.0,
    "markMedianFill": "white",
    "markMedianStroke": "black",
    "markSize": None,
    "markStroke": "black",
    "markStrokeOpacity": 1,
    "markStrokeWidth": None,
    "palette": None,
    "strokeCap": "round",
    "ticks": True,
    "tickSize": 3,
    "transparentBackground": False,
    "viewFill": None,
    "xAxis": True,
    "xDomain": True,
    "xLabels": True,
    "xLabelAngle": 0,
    "xTicks": True,
    "yAxis": True,
    "yDomain": True,
    "yLabels": True,
    "yLabelAngle": 0,
    "yTicks": True,
}


def _find_project_config() -> Path | None:
    """Walk up from cwd to find the nearest dysonsphere.toml."""
    current = Path.cwd()
    while True:
        candidate = current / "dysonsphere.toml"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _config_paths() -> list[Path]:
    """Config file search paths in ascending priority order (user config < project)."""
    paths = []
    xdg_home = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    user_config = xdg_home / "dysonsphere" / "dysonsphere.toml"
    if user_config.exists():
        paths.append(user_config)
    project_config = _find_project_config()
    if project_config is not None:
        paths.append(project_config)
    return paths


def _load_style_overrides(style: str | None) -> dict[str, Any]:
    """Merge [default] and [style] blocks from all config files."""
    merged: dict[str, Any] = {}
    style_found = style is None

    for path in _config_paths():
        with open(path, "rb") as f:
            config: dict[str, Any] = tomllib.load(f)

        for section in ("default", style):
            if section and section in config:
                unknown = set(config[section]) - set(_BUILTIN_DEFAULTS)
                if unknown:
                    raise ValueError(
                        f"Unknown theme parameter(s) in [{section}] of {path}: {sorted(unknown)}"
                    )

        if "default" in config:
            merged.update(config["default"])

        if style is not None and style in config:
            merged.update(config[style])
            style_found = True

    if not style_found:
        raise ValueError(f"Style {style!r} not found in any dysonsphere config file.")

    return merged


def theme(style: str | None = None, **kwargs: Any) -> None:
    """
    Configure and register the dysonsphere Altair theme.

    All parameters are optional — pass only the ones you want to change.
    Everything else uses the dysonsphere built-in defaults.

    A TOML config file can provide persistent per-project or per-user
    overrides. See the README for the config file format and search path.
    Named styles in the config file are selected with ``style=``.
    """
    unknown = set(kwargs) - set(_BUILTIN_DEFAULTS)
    if unknown:
        raise TypeError(f"theme() got unexpected keyword argument(s): {sorted(unknown)}")

    overrides = _load_style_overrides(style)
    p: dict[str, Any] = {**_BUILTIN_DEFAULTS, **overrides, **kwargs}

    # Computed defaults — None means "derive from other params"
    if p["closed"] is None:
        p["closed"] = p["viewFill"] is not None
    if p["markSize"] is None:
        p["markSize"] = min(p["chartWidth"], p["chartHeight"]) * 0.1
    if p["markStrokeWidth"] is None:
        p["markStrokeWidth"] = p["axisWidth"]
    if p["chartFill"] is None and not p["darkmode"]:
        p["chartFill"] = "white"

    palette = p["palette"]
    p["palette"] = colors[palette] if palette is not None and palette in colors else palette

    alt.theme.options = {**p, "tickWidth": p["axisWidth"]}


@alt.theme.register("dysonsphere", enable=True)
def _dysonsphere_theme() -> dict[str, Any]:
    opts = alt.theme.options
    return {
        "background": (
            None if opts["transparentBackground"] else opts["chartFill"]
        ),  # background of the entire chart
        "config": {
            "arc": {
                "fill": opts["markFill"],
                "fillOpacity": opts["markFillOpacity"],
                "stroke": opts["markStroke"],
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "area": {
                "fill": opts["markFill"],
                "fillOpacity": opts["markFillOpacity"],
                "stroke": opts["markStroke"],
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "axis": {
                "domain": True,
                "domainCap": opts["strokeCap"],
                "domainColor": "white" if opts["darkmode"] else "black",
                "domainWidth": opts["axisWidth"],
                "grid": opts["grid"],
                "gridCap": opts["strokeCap"],
                "gridColor": (opts["gridColor"] if opts["darkmode"] else opts["gridColor"]),
                "gridDash": opts["dashedWidth"] if opts["dashedGrid"] else [0, 0],
                "gridOpacity": 1.00,
                "gridWidth": opts["axisWidth"],
                "labelColor": "white" if opts["darkmode"] else "black",
                "labelFont": opts["font"],
                "labelFontSize": opts["fontSize"],
                "labelFontStyle": opts["fontStyle"],
                "labelFontWeight": opts["fontWeight"],
                "offset": 0
                if opts["closed"]
                else (opts["axisOffset"] if opts["axisOffset"] is not None else opts["tickSize"]),
                "ticks": opts["ticks"],
                "tickCap": opts["strokeCap"],
                "tickColor": "white" if opts["darkmode"] else "black",
                "tickSize": opts["tickSize"],
                "tickWidth": opts["axisWidth"],
                "titleColor": "white" if opts["darkmode"] else "black",
                "titleFont": opts["font"],
                "titleFontSize": opts["fontSize"],
                "titleFontStyle": opts["fontStyle"],
                "titleFontWeight": opts["fontWeight"],
            },
            "axisX": {
                "domain": opts["xAxis"] and opts["xDomain"],
                "labelAlign": (
                    "right"
                    if opts["xLabelAngle"] < 0
                    else "left"
                    if opts["xLabelAngle"] > 0
                    else "center"
                ),
                "labelAngle": opts["xLabelAngle"] % 360,
                "labels": opts["xLabels"],
                "ticks": opts["xAxis"] and opts["xTicks"] and opts["ticks"],
                "translate": 0,
            },
            "axisY": {
                "domain": opts["yAxis"] and opts["yDomain"],
                "labelAlign": "center" if opts["yLabelAngle"] != 0 else "right",
                "labelAngle": opts["yLabelAngle"] % 360,
                "labels": opts["yLabels"],
                "ticks": opts["yAxis"] and opts["yTicks"] and opts["ticks"],
                "translate": 0,
            },
            "axisRight": {
                "domain": opts["yAxis"] and opts["yDomain"],
                "labelAlign": "center" if opts["yLabelAngle"] != 0 else "left",
                "labelAngle": (-opts["yLabelAngle"]) % 360,
                "labels": opts["yLabels"],
                "ticks": opts["yAxis"] and opts["yTicks"] and opts["ticks"],
                "translate": 0,
            },
            "axisTop": {
                "domain": opts["xAxis"] and opts["xDomain"],
                "labelAlign": (
                    "left"
                    if opts["xLabelAngle"] < 0
                    else "right"
                    if opts["xLabelAngle"] > 0
                    else "center"
                ),
                "labelAngle": (-opts["xLabelAngle"]) % 360,
                "labels": opts["xLabels"],
                "ticks": opts["xAxis"] and opts["xTicks"] and opts["ticks"],
                "translate": 0,
            },
            "bar": {
                "fill": opts["markFill"],
                "fillOpacity": opts["markFillOpacity"],
                "stroke": opts["markStroke"],
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "boxplot": {
                "size": opts["markSize"] * 0.8,
                "ticks": {
                    "cornerRadius": opts["markStrokeWidth"],
                    "fill": "white" if opts["darkmode"] else "black",
                    "size": opts["markSize"] * 0.6,
                    "thickness": opts["markStrokeWidth"],
                },
                "box": {
                    "fillOpacity": opts["markFillOpacity"],
                    "stroke": opts["markStroke"],
                    "strokeOpacity": opts["markStrokeOpacity"],
                    "strokeWidth": opts["markStrokeWidth"],
                },
                "median": {
                    "fill": opts["markMedianFill"],
                    "fillOpacity": opts["markFillOpacity"],
                    "size": opts["markSize"] * 0.8,
                    "stroke": opts["markMedianStroke"],
                    "strokeOpacity": opts["markStrokeOpacity"],
                    "strokeWidth": opts["markStrokeWidth"],
                },
                "rule": {
                    "fill": "white" if opts["darkmode"] else "black",
                    "fillOpacity": opts["markFillOpacity"],
                    "size": opts["markSize"],
                    "stroke": "white" if opts["darkmode"] else "black",
                    "strokeDash": [0, 0],
                    "strokeOpacity": opts["markStrokeOpacity"],
                    "strokeWidth": opts["markStrokeWidth"],
                },
                "outliers": {
                    "color": "white" if opts["darkmode"] else "black",
                    "fill": "white" if opts["darkmode"] else "black",
                    "fillOpacity": opts["markFillOpacity"],
                    "size": 0,
                    "stroke": opts["markStroke"],
                    "strokeOpacity": opts["markStrokeOpacity"],
                    "strokeWidth": opts["markStrokeWidth"],
                },
            },
            "circle": {
                "fill": "white",
                "fillOpacity": opts["markFillOpacity"],
                "size": opts["markSize"] / 4,
                "stroke": "black" if opts["darkmode"] else opts["markStroke"],
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "errorband": {
                "band": {
                    "fillOpacity": 0.60,
                    "stroke": None,
                    "strokeWidth": opts["markStrokeWidth"],
                    "strokeOpacity": opts["markStrokeOpacity"],
                },
                "borders": {
                    "opacity": 0,
                    "strokeOpacity": opts["markStrokeWidth"],
                    "strokeWidth": opts["markStrokeOpacity"],
                },
            },
            "errorbar": {
                "opacity": 1,
                "rule": {"strokeDash": [0, 0], "strokeWidth": opts["markStrokeWidth"] * 2},
                "ticks": {
                    "color": "white" if opts["darkmode"] else "black",
                    "cornerRadius": opts["markStrokeWidth"],
                    "opacity": 1,
                    "size": opts["markSize"] * 0.6,
                    "thickness": opts["markStrokeWidth"] * 2,
                },
                "thickness": opts["markStrokeWidth"] * 2,
            },
            "font": opts["font"],
            "geoshape": {
                "fill": opts["markFill"],
                "fillOpacity": opts["markFillOpacity"],
                "stroke": "white" if opts["darkmode"] else "black",
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "header": {
                "labelColor": "white" if opts["darkmode"] else "black",
                "labelFont": opts["font"],
                "labelFontSize": opts["fontSize"],
                "labelFontStyle": opts["fontStyle"],
                "labelFontWeight": opts["fontWeight"],
                "titleColor": "white" if opts["darkmode"] else "black",
                "titleFont": opts["font"],
                "titleFontSize": opts["fontSize"],
                "titleFontStyle": opts["fontStyle"],
                "titleFontWeight": opts["fontWeight"],
                "titlePadding": 0,
            },
            "legend": {
                "disable": not opts["legend"],
                "offset": opts["legendOffset"]
                if opts["legendOffset"] is not None
                else opts["tickSize"],
                "gradientLength": opts["markSize"] * 5,
                "gradientThickness": opts["markSize"] * 0.5,
                "gradientOpacity": opts["markFillOpacity"],
                "gradientStrokeColor": "white" if opts["darkmode"] else "black",
                "gradientStrokeWidth": opts["markStrokeWidth"],
                "labelColor": "white" if opts["darkmode"] else "black",
                "labelFont": opts["font"],
                "labelFontSize": opts["fontSize"],
                "labelFontStyle": opts["fontStyle"],
                "labelFontWeight": opts["fontWeight"],
                "strokeColor": "white" if opts["darkmode"] else "black",
                "strokeWidth": opts["axisWidth"] if opts["legendStroke"] else 0,
                "symbolSize": opts["fontSize"] * 6,
                "symbolStrokeColor": "white" if opts["darkmode"] else "black",
                "symbolStrokeWidth": opts["markStrokeWidth"]
                if opts["markStrokeOpacity"] > 0
                else 0,
                "titleColor": "white" if opts["darkmode"] else "black",
                "titleFont": opts["font"],
                "titleFontSize": opts["fontSize"],
                "titleFontStyle": opts["fontStyle"],
                "titleFontWeight": opts["fontWeight"],
            },
            "line": {
                "color": "white" if opts["darkmode"] else "black",
                "stroke": "white" if opts["darkmode"] else "black",
                "strokeCap": opts["strokeCap"],
                "strokeDash": opts["dashedWidth"] if opts["dashedLine"] else [0, 0],
                "strokeOpacity": 1,
                "strokeWidth": opts["axisWidth"] * 1.5,
            },
            "point": {
                "filled": True,
                "fill": opts["markFill"],
                "fillOpacity": opts["markFillOpacity"],
                "size": opts["markSize"] / 2,
                "stroke": opts["markStroke"],
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "range": {
                "category": {
                    "scheme": opts["palette"]
                    if opts.get("palette") is not None
                    else colors["blues"][::2]
                },
                "diverging": {
                    "scheme": opts["palette"]
                    if opts.get("palette") is not None
                    else colors["redsblues"]
                },
                "heatmap": {
                    "scheme": opts["palette"]
                    if opts.get("palette") is not None
                    else colors["blues"]
                },
                "ordinal": {
                    "scheme": opts["palette"]
                    if opts.get("palette") is not None
                    else colors["blues"]
                },
                "ramp": {
                    "scheme": opts["palette"]
                    if opts.get("palette") is not None
                    else colors["blues"]
                },
            },
            "rule": {
                "color": "white" if opts["darkmode"] else "black",
                "stroke": "white" if opts["darkmode"] else "black",
                "strokeCap": opts["strokeCap"],
                "strokeDash": opts["dashedWidth"] if opts["dashedRule"] else [0, 0],
                "strokeOpacity": 1,
                "strokeWidth": opts["axisWidth"],
            },
            "scale": {
                "bandPaddingInner": opts["bandPadding"],
                "bandPaddingOuter": opts["bandPadding"],
                "round": False,
            },
            "rect": {
                "fill": opts["markFill"],
                "fillOpacity": opts["markFillOpacity"],
                "stroke": opts["markStroke"],
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "square": {
                "fill": opts["markFill"],
                "fillOpacity": opts["markFillOpacity"],
                "size": opts["markSize"],
                "stroke": opts["markStroke"],
                "strokeOpacity": opts["markStrokeOpacity"],
                "strokeWidth": opts["markStrokeWidth"],
            },
            "text": {
                "color": "white" if opts["darkmode"] else "black",
                "font": opts["font"],
                "fontSize": opts["fontSize"],
                "fontStyle": opts["fontStyle"],
                "fontWeight": opts["fontWeight"],
            },
            "title": {
                "color": "white" if opts["darkmode"] else "black",
                "font": opts["font"],
                "fontSize": opts["fontSize"],
                "fontStyle": opts["fontStyle"],
                "fontWeight": opts["fontWeight"],
                "subtitleColor": "white" if opts["darkmode"] else "black",
                "subtitleFont": opts["font"],
                "subtitleFontSize": opts["font"],
                "subtitleFontStyle": opts["fontStyle"],
                "subtitleFontWeight": opts["fontWeight"],
            },
            "view": {
                "continuousWidth": opts["chartWidth"],
                "continuousHeight": opts["chartHeight"],
                "discreteWidth": opts["chartWidth"],
                "discreteHeight": opts["chartHeight"],
                "fill": None
                if opts["darkmode"]
                else opts["viewFill"],
                "stroke": ("white" if opts["darkmode"] else "black") if opts["closed"] else None,
                "strokeWidth": opts["axisWidth"],
            },
        },
    }
