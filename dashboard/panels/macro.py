"""Macro Dashboard Panel — yield curve, CPI, Fed funds, recession indicators."""

from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from dashboard.config import COLORS
from dashboard.data.fred import get_yield_curve, get_macro_summary, get_fed_funds_history, get_series
from dashboard.utils.formatting import chart_layout, fmt_price, fmt_pct, change_color


def _build_yield_curve_chart() -> go.Figure:
    """Build yield curve chart: current vs 1Y ago."""
    data = get_yield_curve()
    fig = go.Figure()

    maturities = data.get("maturities", [])
    current = data.get("current", [])
    year_ago = data.get("year_ago", [])

    fig.add_trace(go.Scatter(
        x=maturities, y=current,
        mode="lines+markers",
        name="Current",
        line={"color": COLORS["accent"], "width": 2},
        marker={"size": 6},
    ))
    fig.add_trace(go.Scatter(
        x=maturities, y=year_ago,
        mode="lines+markers",
        name="1Y Ago",
        line={"color": COLORS["text_muted"], "width": 1, "dash": "dash"},
        marker={"size": 4},
    ))

    fig.update_layout(**chart_layout("US TREASURY YIELD CURVE", height=300))
    fig.update_yaxes(title_text="Yield (%)")
    fig.update_xaxes(title_text="Maturity")
    return fig


def _build_fed_funds_chart() -> go.Figure:
    """Build Fed Funds Rate history chart."""
    ff = get_fed_funds_history()
    fig = go.Figure()

    if not ff.empty:
        fig.add_trace(go.Scatter(
            x=ff.index, y=ff.values,
            mode="lines",
            name="Fed Funds Rate",
            line={"color": COLORS["accent"], "width": 2},
            fill="tozeroy",
            fillcolor="rgba(255, 152, 0, 0.1)",
        ))

    fig.update_layout(**chart_layout("FED FUNDS RATE", height=250))
    fig.update_yaxes(title_text="%")
    return fig


def _build_inflation_chart() -> go.Figure:
    """Build CPI and PCE YoY chart."""
    from datetime import datetime, timedelta
    start = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    cpi = get_series("CPIAUCSL", start=start)
    pce = get_series("PCEPI", start=start)

    fig = go.Figure()

    if not cpi.empty and len(cpi) > 12:
        cpi_yoy = cpi.pct_change(12) * 100
        fig.add_trace(go.Scatter(
            x=cpi_yoy.index, y=cpi_yoy.values,
            mode="lines", name="CPI YoY",
            line={"color": COLORS["red"], "width": 2},
        ))

    if not pce.empty and len(pce) > 12:
        pce_yoy = pce.pct_change(12) * 100
        fig.add_trace(go.Scatter(
            x=pce_yoy.index, y=pce_yoy.values,
            mode="lines", name="PCE YoY",
            line={"color": COLORS["cyan"], "width": 2},
        ))

    # 2% target line
    fig.add_hline(y=2, line_dash="dot", line_color=COLORS["text_muted"],
                  annotation_text="2% Target", annotation_font_color=COLORS["text_muted"])

    fig.update_layout(**chart_layout("INFLATION — CPI vs PCE YoY %", height=250))
    fig.update_yaxes(title_text="%")
    return fig


def _macro_indicator_card(label: str, data: dict) -> dbc.Col:
    """Create a small indicator card for macro data."""
    value = data.get("value")
    change = data.get("change")
    date = data.get("date", "")
    yoy = data.get("yoy")

    display_val = f"{value}" if value is not None else "—"
    if yoy is not None:
        display_val = f"{yoy}% YoY"

    return dbc.Col(
        html.Div([
            html.Div(label, style={
                "fontSize": "9px", "color": COLORS["accent"],
                "textTransform": "uppercase", "letterSpacing": "0.5px",
            }),
            html.Div(display_val, style={
                "fontSize": "16px", "fontWeight": "bold",
                "color": COLORS["text"], "fontFamily": "monospace",
            }),
            html.Div(f"Chg: {change}" if change is not None else "", style={
                "fontSize": "9px",
                "color": change_color(change) if change else COLORS["text_muted"],
            }),
            html.Div(date or "", style={"fontSize": "8px", "color": COLORS["text_muted"]}),
        ], style={
            "padding": "8px",
            "backgroundColor": COLORS["card_bg"],
            "border": f"1px solid {COLORS['border']}",
            "borderRadius": "2px",
        }),
        md=2, sm=4, xs=6,
        className="mb-2",
    )


def layout():
    """Return the macro dashboard layout."""
    return html.Div([
        html.Div("MACRO DASHBOARD", style={
            "fontSize": "11px", "color": COLORS["accent"],
            "letterSpacing": "2px", "marginBottom": "8px", "fontWeight": "bold",
        }),

        # Macro indicators row
        dbc.Row(id="macro-indicators-row", className="mb-3"),

        # Recession flags
        html.Div(id="macro-recession-flags", className="mb-3"),

        # Charts
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="yield-curve-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=6),
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="inflation-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=6),
        ]),

        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="fed-funds-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=6),
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="credit-spreads-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=6),
        ]),

        # Hidden interval for refresh
        dcc.Interval(id="macro-interval", interval=300_000, n_intervals=0),
    ])


def register_callbacks(app):
    @app.callback(
        [Output("macro-indicators-row", "children"),
         Output("macro-recession-flags", "children"),
         Output("yield-curve-chart", "figure"),
         Output("inflation-chart", "figure"),
         Output("fed-funds-chart", "figure"),
         Output("credit-spreads-chart", "figure")],
        Input("macro-interval", "n_intervals"),
    )
    def update_macro(_n):
        summary = get_macro_summary()

        # Indicator cards
        display_keys = ["Fed Funds Rate", "CPI YoY", "PCE YoY", "Unemployment",
                        "Real GDP Growth", "M2 Money Supply"]
        cards = []
        for key in display_keys:
            if key in summary:
                cards.append(_macro_indicator_card(key, summary[key]))

        # Recession flags
        inverted = summary.get("_yield_curve_inverted", False)
        spread_10y2y = summary.get("_10y2y_spread")
        spread_10y3m = summary.get("_10y3m_spread")
        sahm = summary.get("Sahm Rule", {})
        sahm_val = sahm.get("value")

        flags = []
        if inverted:
            flags.append(html.Span("⚠ YIELD CURVE INVERTED  ", style={
                "color": COLORS["red"], "fontSize": "11px", "fontWeight": "bold",
            }))
        if spread_10y2y is not None:
            flags.append(html.Span(f"10Y-2Y: {spread_10y2y}bp  ", style={
                "color": change_color(spread_10y2y), "fontSize": "11px",
            }))
        if spread_10y3m is not None:
            flags.append(html.Span(f"10Y-3M: {spread_10y3m}bp  ", style={
                "color": change_color(spread_10y3m), "fontSize": "11px",
            }))
        if sahm_val is not None:
            sahm_color = COLORS["red"] if sahm_val >= 0.5 else COLORS["green"]
            flags.append(html.Span(f"Sahm Rule: {sahm_val}  ", style={
                "color": sahm_color, "fontSize": "11px",
            }))
            if sahm_val >= 0.5:
                flags.append(html.Span("⚠ RECESSION SIGNAL  ", style={
                    "color": COLORS["red"], "fontSize": "11px", "fontWeight": "bold",
                }))

        recession_div = html.Div(
            flags,
            style={
                "padding": "6px 12px",
                "backgroundColor": COLORS["card_bg"],
                "border": f"1px solid {COLORS['border']}",
                "borderRadius": "2px",
            },
        ) if flags else html.Div()

        # Charts
        yield_curve_fig = _build_yield_curve_chart()
        inflation_fig = _build_inflation_chart()
        fed_funds_fig = _build_fed_funds_chart()

        # Credit spreads chart
        from datetime import datetime, timedelta
        start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
        hy = get_series("BAMLH0A0HYM2", start=start)
        ig = get_series("BAMLC0A0CM", start=start)

        cs_fig = go.Figure()
        if not hy.empty:
            cs_fig.add_trace(go.Scatter(
                x=hy.index, y=hy.values,
                mode="lines", name="HY Spread",
                line={"color": COLORS["red"], "width": 2},
            ))
        if not ig.empty:
            cs_fig.add_trace(go.Scatter(
                x=ig.index, y=ig.values,
                mode="lines", name="IG Spread",
                line={"color": COLORS["blue"], "width": 2},
            ))
        cs_fig.update_layout(**chart_layout("CREDIT SPREADS — HY vs IG (OAS)", height=250))
        cs_fig.update_yaxes(title_text="bps")

        return cards, recession_div, yield_curve_fig, inflation_fig, fed_funds_fig, cs_fig
