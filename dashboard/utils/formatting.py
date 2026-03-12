"""Formatting utilities for the dashboard."""

from dashboard.config import COLORS


def fmt_price(val, decimals=2):
    """Format a price value."""
    if val is None:
        return "—"
    return f"{val:,.{decimals}f}"


def fmt_pct(val, decimals=2):
    """Format a percentage value."""
    if val is None:
        return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.{decimals}f}%"


def fmt_change(val, decimals=2):
    """Format a change value with sign."""
    if val is None:
        return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:,.{decimals}f}"


def fmt_large_number(val):
    """Format large numbers (market cap, etc.) with B/M/K suffixes."""
    if val is None:
        return "—"
    if abs(val) >= 1e12:
        return f"${val / 1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"${val / 1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val / 1e6:.2f}M"
    if abs(val) >= 1e3:
        return f"${val / 1e3:.1f}K"
    return f"${val:,.0f}"


def change_color(val):
    """Return green/red color based on positive/negative value."""
    if val is None or val == 0:
        return COLORS["text_muted"]
    return COLORS["green"] if val > 0 else COLORS["red"]


def chart_layout(title="", height=400, **kwargs):
    """Return a standard Plotly layout dict with Bloomberg styling."""
    layout = {
        "template": "plotly_dark",
        "paper_bgcolor": COLORS["card_bg"],
        "plot_bgcolor": COLORS["card_bg"],
        "font": {"family": "JetBrains Mono, Consolas, monospace", "color": COLORS["text"], "size": 11},
        "title": {"text": title, "font": {"color": COLORS["accent"], "size": 14}},
        "height": height,
        "margin": {"l": 50, "r": 20, "t": 40, "b": 40},
        "xaxis": {
            "gridcolor": COLORS["border"],
            "zerolinecolor": COLORS["border"],
        },
        "yaxis": {
            "gridcolor": COLORS["border"],
            "zerolinecolor": COLORS["border"],
        },
        "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"size": 10}},
    }
    layout.update(kwargs)
    return layout
