"""Shared chart colours for the dashboard and exported charts (Goggy's theme, 2026-10-30). Display only.

The strategy line is Deep Burgundy; buy-and-hold is Muted Sage Grey, drawn thicker and dashed so it stays distinct in
greyscale (sage on the cream page is only 2.14:1, so the dash — not the colour — carries the difference); any extra
series (cash / invested, fees / spread) use darker sage and tan.
"""

import altair as alt

STRATEGY = "#590907"
BUY_AND_HOLD = "#A5A79B"
EXTRA = ("#6F7264", "#B8956A")


def series_lines(series: list[str], benchmark: str | None = None, title: str = "Series") -> dict:
    """Altair encodings for line charts: the first series is the strategy (burgundy, solid); `benchmark` (if present)
    is sage, thicker and dashed. Use as `chart.encode(x=..., y=..., **series_lines(names, benchmark))`."""
    others = [s for s in series if s != benchmark]
    domain = others + ([benchmark] if benchmark in series else [])
    colours = [STRATEGY, *EXTRA][: len(others)] + ([BUY_AND_HOLD] if benchmark in series else [])
    dashes = [[1, 0]] * len(others) + ([[6, 4]] if benchmark in series else [])
    widths = [2] * len(others) + ([3.5] if benchmark in series else [])
    field = "series:N"
    return {
        "color": alt.Color(field, title=title, scale=alt.Scale(domain=domain, range=colours)),
        # same field + same title → Vega-Lite merges the three into ONE legend that also shows the dash
        "strokeDash": alt.StrokeDash(
            field, title=title, scale=alt.Scale(domain=domain, range=dashes)
        ),
        "strokeWidth": alt.StrokeWidth(
            field, title=title, scale=alt.Scale(domain=domain, range=widths)
        ),
    }


def extra_colours(names: list[str], field: str, title: str = "") -> alt.Color:
    """Colour encoding for non-strategy series (e.g. Cash / Invested, Fees / Spread): darker sage, then tan."""
    return alt.Color(
        f"{field}:N", title=title, scale=alt.Scale(domain=names, range=list(EXTRA[: len(names)]))
    )
