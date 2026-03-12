"""FX & Commodities Panel — currency matrix and commodity charts."""

from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from dashboard.config import COLORS, FX_PAIRS, COMMODITIES
from dashboard.data.market import get_quote, get_history
from dashboard.utils.formatting import (
    chart_layout, fmt_price, fmt_pct, fmt_change, change_color,
)


def _make_asset_row(label: str, symbol: str) -> dict:
    """Build data for a single asset row."""
    quote = get_quote(symbol)

    # Get period returns
    periods = {"1D": "1d", "1W": "5d", "1M": "1mo", "YTD": "ytd"}
    pct_changes = {}
    for plabel, period in periods.items():
        hist = get_history(symbol, period=period)
        if not hist.empty and len(hist) > 1:
            ret = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
            pct_changes[plabel] = round(ret, 2)
        else:
            pct_changes[plabel] = None

    return {
        "label": label,
        "symbol": symbol,
        "price": quote.get("price"),
        "change": quote.get("change"),
        "pct_change": quote.get("pct_change"),
        **pct_changes,
    }


def _build_mini_chart(symbol: str, label: str) -> go.Figure:
    """Build a small sparkline chart for an asset."""
    hist = get_history(symbol, period="3mo")
    fig = go.Figure()

    if not hist.empty:
        color = COLORS["green"] if hist["Close"].iloc[-1] >= hist["Close"].iloc[0] else COLORS["red"]
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["Close"],
            mode="lines", name=label,
            line={"color": color, "width": 1.5},
            fill="tozeroy",
            fillcolor=f"rgba({','.join(str(int(color.lstrip('#')[i:i+2], 16)) for i in (0, 2, 4))}, 0.1)",
        ))

    fig.update_layout(
        **chart_layout("", height=120),
        margin={"l": 5, "r": 5, "t": 5, "b": 5},
        xaxis={"visible": False},
        yaxis={"visible": False},
        showlegend=False,
    )
    return fig


def _asset_table_row(data: dict) -> html.Tr:
    """Create a table row for an asset."""
    cells = [
        html.Td(data["label"], style={
            "color": COLORS["accent"], "fontSize": "11px", "fontWeight": "bold",
            "padding": "6px 10px",
        }),
        html.Td(fmt_price(data["price"], 4), style={
            "color": COLORS["text"], "fontSize": "12px", "fontFamily": "monospace",
            "padding": "6px 10px", "textAlign": "right",
        }),
        html.Td(fmt_change(data["change"], 4), style={
            "color": change_color(data["change"]), "fontSize": "11px",
            "fontFamily": "monospace", "padding": "6px 10px", "textAlign": "right",
        }),
    ]

    for period in ["1D", "1W", "1M", "YTD"]:
        val = data.get(period)
        cells.append(html.Td(
            fmt_pct(val) if val is not None else "—",
            style={
                "color": change_color(val) if val is not None else COLORS["text_muted"],
                "fontSize": "11px", "fontFamily": "monospace",
                "padding": "6px 10px", "textAlign": "right",
            },
        ))

    return html.Tr(cells, style={"borderBottom": f"1px solid {COLORS['border']}"})


def layout():
    """Return the FX & Commodities panel layout."""
    return html.Div([
        dcc.Interval(id="fxcomm-interval", interval=120_000, n_intervals=0),

        # FX Section
        html.Div("FOREIGN EXCHANGE", style={
            "fontSize": "11px", "color": COLORS["accent"],
            "letterSpacing": "2px", "marginBottom": "8px", "fontWeight": "bold",
        }),
        html.Div(id="fx-table-container", className="mb-4"),

        dbc.Row(id="fx-charts-row", className="mb-4"),

        # Commodities Section
        html.Div("COMMODITIES", style={
            "fontSize": "11px", "color": COLORS["accent"],
            "letterSpacing": "2px", "marginBottom": "8px", "fontWeight": "bold",
        }),
        html.Div(id="comm-table-container", className="mb-3"),

        dbc.Row(id="comm-charts-row"),
    ])


def register_callbacks(app):
    @app.callback(
        [Output("fx-table-container", "children"),
         Output("fx-charts-row", "children"),
         Output("comm-table-container", "children"),
         Output("comm-charts-row", "children")],
        Input("fxcomm-interval", "n_intervals"),
    )
    def update_fxcomm(_n):
        # FX table
        fx_rows = []
        fx_charts = []
        for label, symbol in FX_PAIRS.items():
            data = _make_asset_row(label, symbol)
            fx_rows.append(_asset_table_row(data))
            fx_charts.append(dbc.Col([
                html.Div(label, style={"fontSize": "9px", "color": COLORS["accent"], "textAlign": "center"}),
                dcc.Graph(figure=_build_mini_chart(symbol, label), config={"displayModeBar": False}),
            ], md=2, sm=4, xs=6))

        fx_header = html.Tr([
            html.Th(h, style={
                "color": COLORS["text_muted"], "fontSize": "9px", "padding": "4px 10px",
                "textAlign": "right" if i > 0 else "left",
                "borderBottom": f"1px solid {COLORS['accent']}",
            })
            for i, h in enumerate(["PAIR", "PRICE", "CHG", "1D", "1W", "1M", "YTD"])
        ])

        fx_table = html.Table(
            [html.Thead(fx_header), html.Tbody(fx_rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        )

        # Commodities table
        comm_rows = []
        comm_charts = []
        for label, symbol in COMMODITIES.items():
            data = _make_asset_row(label, symbol)
            comm_rows.append(_asset_table_row(data))
            comm_charts.append(dbc.Col([
                html.Div(label, style={"fontSize": "9px", "color": COLORS["accent"], "textAlign": "center"}),
                dcc.Graph(figure=_build_mini_chart(symbol, label), config={"displayModeBar": False}),
            ], md=2, sm=4, xs=6))

        comm_table = html.Table(
            [html.Thead(fx_header), html.Tbody(comm_rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        )

        return fx_table, fx_charts, comm_table, comm_charts
