from pathlib import Path

import altair as alt


def save(
    chart: alt.Chart,
    filename: str,
    ppi: int = 1200,
    description: str | None = None,
    save_vega_spec: bool = True,
) -> None:
    """
    Save a chart as light and dark PNG and SVG files.

    Produces four files from a single call:

    - ``<filename>_light.png`` and ``<filename>_light.svg``
    - ``<filename>_dark.png`` and ``<filename>_dark.svg``

    Dark and light versions are rendered by temporarily toggling
    ``darkmode`` in the theme options, leaving all other options intact.

    Parameters
    ----------
    chart:
        The Altair chart to save.
    filename:
        Extensionless path for the output files (e.g. ``"myplot"`` or
        ``"plots/myplot"``). A bare name saves to the current working
        directory, matching Altair's default behaviour.
    ppi:
        Pixel density for PNG output.
    description:
        Optional description embedded in the chart via ``chart.properties(description=...)``.
        Appears as a ``<desc>`` element in SVG output.
    save_vega_spec:
        If ``True``, also writes ``<filename>.json`` containing the full Vega-Lite spec.

    Examples
    --------
    ::

        theme.options()
        chart = alt.Chart(df).mark_point().encode(...)
        theme.save(chart, "plots/myplot")
        # writes: plots/myplot_light.png, plots/myplot_light.svg,
        #         plots/myplot_dark.png,  plots/myplot_dark.svg
    """
    if not alt.theme.options:
        raise RuntimeError("theme.options() must be called before theme.save().")

    if description is not None:
        chart = chart.properties(description=description)

    base = Path(filename)
    original_darkmode = alt.theme.options.get("darkmode", False)
    original_transparent = alt.theme.options.get("transparentBackground", False)

    if save_vega_spec:
        chart.save(str(base.parent / f"{base.name}_vegalite.json"))

    try:
        import vl_convert as vlc

        alt.theme.options["transparentBackground"] = True
        for mode, suffix in [(False, "_light"), (True, "_dark")]:
            alt.theme.options["darkmode"] = mode
            svg_path = str(base.parent / f"{base.name}{suffix}.svg")
            chart.save(svg_path)
            _fix_tick_alignment(
                svg_path,
                band_padding=alt.theme.options.get("bandPadding", 0.1),
                chart_width=alt.theme.options.get("chartWidth", 100),
            )
            _simplify_svg(svg_path)
            with open(svg_path, encoding="utf-8") as f:
                svg_content = f.read()
            png_path = str(base.parent / f"{base.name}{suffix}.png")
            Path(png_path).write_bytes(vlc.svg_to_png(svg_content, ppi=ppi))
    finally:
        alt.theme.options["darkmode"] = original_darkmode
        alt.theme.options["transparentBackground"] = original_transparent


def _fix_tick_alignment(
    path: str, band_padding: float = 0.1, chart_width: float = 100.0
) -> None:
    """Move x-axis tick lines from Vega's floor'd integer positions to exact mark centers.

    Vega snaps axis tick group transforms to integers for crisp screen rendering but
    keeps mark coordinates as floats.  At high DPI (scale ≥ 4) this produces visible
    misalignment.

    For bar charts: tick centers are read from the bar path data (aria-roledescription="bar").
    For all other charts (strip, violin, etc.): band centers are computed analytically
    from the number of categories and theme scale parameters, then ticks are moved to
    those float positions.  A validation step ensures the fix is only applied to nominal
    band scales — quantitative and time axes are left untouched.
    """
    import re
    import xml.etree.ElementTree as ET

    NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

    tree = ET.parse(path)
    root = tree.getroot()

    # --- bar charts: read centers from path data ---
    bar_centers: list[float] = []
    for el in root.iter(f"{{{NS}}}path"):
        if el.get("aria-roledescription") != "bar":
            continue
        d = el.get("d", "")
        m = re.match(r"M([\d.]+),[-\d.e+]+h([\d.]+)", d)
        if m:
            bar_centers.append(round(float(m.group(1)) + float(m.group(2)) / 2, 4))

    if bar_centers:
        unique_centers = sorted(set(bar_centers))

        def nearest(tick_x: float) -> float | None:
            c = min(unique_centers, key=lambda v: abs(v - tick_x))
            return c if abs(c - tick_x) < 2.0 else None

        def apply_bar_fix(el: ET.Element) -> None:
            for child in el:
                if child.get("class", "") == "mark-rule role-axis-tick":
                    for line in child:
                        t = line.get("transform", "")
                        m = re.match(r"translate\((\d+(?:\.\d+)?),0\)$", t)
                        if m:
                            c = nearest(float(m.group(1)))
                            if c is not None:
                                line.set("transform", f"translate({c},0)")
                else:
                    apply_bar_fix(child)

        apply_bar_fix(root)

    else:
        # --- non-bar charts: compute band centers analytically ---
        # Collect integer tick x positions from all x-axis tick groups.
        tick_xs: list[float] = []

        def collect_ticks(el: ET.Element) -> None:
            for child in el:
                if child.get("class", "") == "mark-rule role-axis-tick":
                    for line in child:
                        t = line.get("transform", "")
                        m = re.match(r"translate\((\d+(?:\.\d+)?),0\)$", t)
                        if m:
                            v = float(m.group(1))
                            if v > 0:
                                tick_xs.append(v)
                else:
                    collect_ticks(child)

        collect_ticks(root)
        if not tick_xs:
            return

        # With xOffset encoding Vega sets paddingInner=0, so
        # step = chart_width / (n + 2·paddingOuter)
        # band_center_i = step · (paddingOuter + i + 0.5)
        n = len(tick_xs)
        step = chart_width / (n + 2 * band_padding)
        sorted_ticks = sorted(tick_xs)

        # Validate that tick positions match expected band-scale floor positions.
        # Quantitative/time axes also produce evenly-spaced ticks but at different
        # pixel positions — if they don't match, this is not a nominal band scale.
        expected = [int(step * (band_padding + i + 0.5)) for i in range(n)]
        if [int(t) for t in sorted_ticks] != expected:
            return

        center_map = {
            t: round(step * (band_padding + i + 0.5), 4)
            for i, t in enumerate(sorted_ticks)
        }

        def apply_analytic_fix(el: ET.Element) -> None:
            for child in el:
                if child.get("class", "") == "mark-rule role-axis-tick":
                    for line in child:
                        t = line.get("transform", "")
                        m = re.match(r"translate\((\d+(?:\.\d+)?),0\)$", t)
                        if m:
                            c = center_map.get(float(m.group(1)))
                            if c is not None:
                                line.set("transform", f"translate({c},0)")
                else:
                    apply_analytic_fix(child)

        apply_analytic_fix(root)

    with open(path, "w", encoding="utf-8") as f:
        f.write(ET.tostring(root, encoding="unicode"))


def _simplify_svg(path: str) -> None:
    """
    Reduce SVG grouping depth by inlining structurally redundant ``<g>`` elements.

    Altair/Vega generates deeply nested ``<g>`` wrappers for its internal mark
    grouping system (e.g. ``role-frame``, ``role-mark``, ``mark-symbol``). These
    groups carry only a ``class`` attribute and have no effect on visual output,
    but they require extra double-clicks to navigate in Adobe Illustrator and
    other SVG editors.

    This function removes those wrappers by inlining their children directly into
    the parent element. Groups that carry any of the following attributes are
    preserved because they affect rendering or layout: ``transform``,
    ``clip-path``, ``opacity``, ``mask``, ``filter``, ``style``, ``id``.
    Definition blocks (``<defs>``, ``<clipPath>``, ``<symbol>``) are left
    entirely untouched.

    The result is a flatter, editor-friendly SVG that renders identically to the
    original.
    """
    import xml.etree.ElementTree as ET

    NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

    KEEP_ATTRS = {"transform", "clip-path", "opacity", "mask", "filter", "style", "id"}
    SKIP_TAGS = {f"{{{NS}}}defs", f"{{{NS}}}clipPath", f"{{{NS}}}symbol"}

    def _flatten(parent):
        if parent.tag in SKIP_TAGS:
            return
        i = 0
        while i < len(parent):
            child = parent[i]
            _flatten(child)
            if child.tag == f"{{{NS}}}g" and not (set(child.attrib) & KEEP_ATTRS):
                grandchildren = list(child)
                parent.remove(child)
                for j, gc in enumerate(grandchildren):
                    parent.insert(i + j, gc)
                if not grandchildren:
                    i += 1
            else:
                i += 1

    tree = ET.parse(path)
    _flatten(tree.getroot())
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(ET.tostring(tree.getroot(), encoding="unicode"))
