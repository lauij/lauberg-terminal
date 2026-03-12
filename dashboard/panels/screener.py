"""Screener / Comparator Panel — compare up to 5 tickers side by side."""

import io
import base64

from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from dashboard.config import COLORS
from dashboard.data.market import get_history, get_ticker_info
from dashboard.utils.formatting import (
    chart_layout, fmt_price, fmt_pct, fmt_large_number,
)


def _build_normalized_chart(tickers: list[str], period: str) -> go.Figure:
    """Build a normalized price performance chart (rebased to 100)."""
    fig = go.Figure()
    colors = [COLORS["accent"], COLORS["blue"], COLORS["cyan"], COLORS["green"], COLORS["red"]]

    for i, t in enumerate(tickers[:5]):
        hist = get_history(t, period=period)
        if not hist.empty:
            normalized = hist["Close"] / hist["Close"].iloc[0] * 100
            fig.add_trace(go.Scatter(
                x=normalized.index, y=normalized.values,
                mode="lines", name=t,
                line={"color": colors[i % len(colors)], "width": 2},
            ))

    fig.add_hline(y=100, line_dash="dot", line_color=COLORS["text_muted"])
    fig.update_layout(**chart_layout("NORMALIZED PERFORMANCE (Base 100)", height=380))
    fig.update_yaxes(title_text="Indexed (100)")
    return fig


def _build_comparison_table(tickers: list[str]) -> html.Table:
    """Build a side-by-side comparison table of key multiples."""
    metrics = [
        ("Market Cap", "marketCap", True, False),
        ("P/E (TTM)", "trailingPE", False, False),
        ("P/E (FWD)", "forwardPE", False, False),
        ("EV/EBITDA", "enterpriseToEbitda", False, False),
        ("PEG Ratio", "pegRatio", False, False),
        ("P/B", "priceToBook", False, False),
        ("Rev Growth", "revenueGrowth", False, True),
        ("Gross Margin", "grossMargins", False, True),
        ("Op Margin", "operatingMargins", False, True),
        ("Net Margin", "profitMargins", False, True),
        ("ROE", "returnOnEquity", False, True),
        ("Beta", "beta", False, False),
        ("Div Yield", "dividendYield", False, True),
    ]

    infos = {}
    for t in tickers[:5]:
        infos[t] = get_ticker_info(t)

    # Header row
    header = html.Tr(
        [html.Th("METRIC", style={
            "color": COLORS["accent"], "fontSize": "10px", "padding": "4px 8px",
            "borderBottom": f"1px solid {COLORS['accent']}",
        })] +
        [html.Th(t, style={
            "color": COLORS["accent"], "fontSize": "10px", "padding": "4px 8px",
            "textAlign": "right", "borderBottom": f"1px solid {COLORS['accent']}",
        }) for t in tickers[:5]]
    )

    rows = []
    for label, key, is_money, is_pct in metrics:
        cells = [html.Td(label, style={
            "color": COLORS["text_muted"], "fontSize": "11px", "padding": "4px 8px",
        })]
        for t in tickers[:5]:
            val = infos.get(t, {}).get(key)
            if val is None:
                display = "—"
            elif is_money:
                display = fmt_large_number(val)
            elif is_pct:
                display = fmt_pct(val * 100 if abs(val) < 1 else val)
            else:
                display = fmt_price(val)
            cells.append(html.Td(display, style={
                "color": COLORS["text"], "fontSize": "11px", "fontFamily": "monospace",
                "padding": "4px 8px", "textAlign": "right",
            }))
        rows.append(html.Tr(cells, style={"borderBottom": f"1px solid {COLORS['border']}"}))

    return html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )


def _generate_csv(tickers: list[str]) -> str:
    """Generate CSV data for comparison."""
    infos = {t: get_ticker_info(t) for t in tickers[:5]}
    rows = []
    keys = ["shortName", "sector", "marketCap", "trailingPE", "forwardPE",
            "enterpriseToEbitda", "revenueGrowth", "grossMargins", "operatingMargins",
            "profitMargins", "returnOnEquity", "beta", "dividendYield"]
    for key in keys:
        row = {"Metric": key}
        for t in tickers[:5]:
            row[t] = infos.get(t, {}).get(key, "")
        rows.append(row)
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def layout():
    """Return the screener layout."""
    return html.Div([
        html.Div("SCREENER / COMPARATOR", style={
            "fontSize": "11px", "color": COLORS["accent"],
            "letterSpacing": "2px", "marginBottom": "8px", "fontWeight": "bold",
        }),

        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("COMPARE", style={
                        "backgroundColor": COLORS["accent"], "color": "#000",
                        "fontWeight": "bold", "fontSize": "11px",
                    }),
                    dbc.Input(
                        id="screener-tickers",
                        value="AAPL, MSFT, GOOGL, AMZN, META",
                        placeholder="Up to 5 tickers...",
                        style={"backgroundColor": COLORS["input_bg"], "color": COLORS["text"],
                               "border": f"1px solid {COLORS['border']}", "fontFamily": "monospace"},
                        debounce=True,
                    ),
                ], size="sm"),
            ], md=6),
            dbc.Col([
                dbc.Select(
                    id="screener-period",
                    options=[
                        {"label": "1M", "value": "1mo"},
                        {"label": "3M", "value": "3mo"},
                        {"label": "1Y", "value": "1y"},
                        {"label": "3Y", "value": "3y"},
                        {"label": "5Y", "value": "5y"},
                    ],
                    value="1y",
                    style={"backgroundColor": COLORS["input_bg"], "color": COLORS["text"],
                           "border": f"1px solid {COLORS['border']}", "fontSize": "11px"},
                ),
            ], md=2),
            dbc.Col([
                dbc.Button(
                    "Export CSV", id="screener-export-btn", size="sm",
                    color="warning", outline=True,
                ),
                dcc.Download(id="screener-download"),
            ], md=2),
        ], className="mb-3 align-items-center"),

        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="screener-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=7),
            dbc.Col([
                html.Div(id="screener-table-container"),
            ], md=5),
        ]),
    ])


def register_callbacks(app):
    @app.callback(
        [Output("screener-chart", "figure"),
         Output("screener-table-container", "children")],
        [Input("screener-tickers", "value"),
         Input("screener-period", "value")],
    )
    def update_screener(tickers_str, period):
        if not tickers_str:
            empty = go.Figure()
            empty.update_layout(**chart_layout("Enter tickers above", height=380))
            return empty, html.Div()

        tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()][:5]
        chart = _build_normalized_chart(tickers, period)
        table = _build_comparison_table(tickers)
        return chart, table

    @app.callback(
        Output("screener-download", "data"),
        Input("screener-export-btn", "n_clicks"),
        Input("screener-tickers", "value"),
        prevent_initial_call=True,
    )
    def export_csv(n_clicks, tickers_str):
        if not n_clicks or not tickers_str:
            return None
        tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()][:5]
        csv = _generate_csv(tickers)
        return {"content": csv, "filename": "screener_comparison.csv"}
