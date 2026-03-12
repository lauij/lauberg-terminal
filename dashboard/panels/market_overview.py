"""Market Overview Panel — top bar with major indices, commodities, FX."""

from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc

from dashboard.config import COLORS, MARKET_TICKERS, REFRESH_INTERVAL_MS
from dashboard.data.market import get_multiple_quotes
from dashboard.utils.formatting import fmt_price, fmt_pct, fmt_change, change_color


def _make_ticker_card(label: str, data: dict) -> dbc.Col:
    """Create a single ticker card for the market bar."""
    price = data.get("price")
    change = data.get("change")
    pct = data.get("pct_change")
    color = change_color(pct)
    stale = data.get("stale", False)

    return dbc.Col(
        html.Div(
            [
                html.Div(label, style={
                    "fontSize": "10px",
                    "color": COLORS["text_muted"],
                    "textTransform": "uppercase",
                    "letterSpacing": "1px",
                }),
                html.Div(fmt_price(price), style={
                    "fontSize": "16px",
                    "fontWeight": "bold",
                    "color": COLORS["text"],
                    "fontFamily": "JetBrains Mono, Consolas, monospace",
                }),
                html.Div(
                    f"{fmt_change(change)} ({fmt_pct(pct)})",
                    style={
                        "fontSize": "11px",
                        "color": color,
                        "fontFamily": "JetBrains Mono, Consolas, monospace",
                    },
                ),
                html.Div("⚠ CACHED", style={
                    "fontSize": "8px", "color": COLORS["accent"],
                    "display": "block" if stale else "none",
                }),
            ],
            style={
                "padding": "8px 12px",
                "borderRight": f"1px solid {COLORS['border']}",
                "textAlign": "center",
                "minWidth": "120px",
            },
        ),
        width="auto",
    )


def layout():
    """Return the market overview bar layout."""
    return html.Div(
        [
            dcc.Interval(
                id="market-interval",
                interval=REFRESH_INTERVAL_MS,
                n_intervals=0,
            ),
            dbc.Row(
                id="market-ticker-row",
                className="g-0 flex-nowrap",
                style={"overflowX": "auto"},
            ),
        ],
        style={
            "backgroundColor": COLORS["header_bg"],
            "borderBottom": f"2px solid {COLORS['accent']}",
            "padding": "4px 0",
        },
    )


def register_callbacks(app):
    @app.callback(
        Output("market-ticker-row", "children"),
        Input("market-interval", "n_intervals"),
    )
    def update_market_bar(_n):
        quotes = get_multiple_quotes(MARKET_TICKERS)
        cards = [_make_ticker_card(label, data) for label, data in quotes.items()]
        return cards
