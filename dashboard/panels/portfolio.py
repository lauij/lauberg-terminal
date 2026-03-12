"""Portfolio Tracker Panel — performance, risk metrics, attribution."""

from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
import pandas as pd

from dashboard.config import COLORS
from dashboard.data.market import get_history, get_ticker_info
from dashboard.utils.formatting import chart_layout, fmt_pct, fmt_price, change_color


def _compute_portfolio_metrics(tickers: list[str], weights: list[float], period: str = "1y"):
    """Compute portfolio performance, risk metrics, correlation."""
    returns_data = {}
    for t in tickers:
        hist = get_history(t, period=period)
        if not hist.empty:
            returns_data[t] = hist["Close"].pct_change().dropna()

    if not returns_data:
        return None

    # Align all series
    df = pd.DataFrame(returns_data).dropna()
    if df.empty:
        return None

    # Portfolio returns
    w = np.array(weights[:len(df.columns)])
    w = w / w.sum()  # normalize
    port_returns = (df * w).sum(axis=1)

    # Benchmark (SPY)
    spy = get_history("SPY", period=period)
    bench_returns = spy["Close"].pct_change().dropna() if not spy.empty else pd.Series(dtype=float)

    # Align benchmark
    common = port_returns.index.intersection(bench_returns.index)
    port_returns_aligned = port_returns.loc[common]
    bench_returns_aligned = bench_returns.loc[common]

    # Cumulative returns
    port_cum = (1 + port_returns_aligned).cumprod() - 1
    bench_cum = (1 + bench_returns_aligned).cumprod() - 1

    # Risk metrics (annualized)
    trading_days = 252
    port_annual_return = port_returns_aligned.mean() * trading_days
    port_annual_vol = port_returns_aligned.std() * np.sqrt(trading_days)
    risk_free = 0.04  # approximate
    sharpe = (port_annual_return - risk_free) / port_annual_vol if port_annual_vol > 0 else 0

    # Max drawdown
    cum_val = (1 + port_returns_aligned).cumprod()
    peak = cum_val.cummax()
    drawdown = (cum_val - peak) / peak
    max_dd = drawdown.min()

    # Correlation matrix
    corr = df.corr()

    # Sector exposure
    sectors = {}
    for i, t in enumerate(df.columns):
        info = get_ticker_info(t)
        sector = info.get("sector", "Unknown")
        sectors[sector] = sectors.get(sector, 0) + w[i]

    return {
        "port_cum": port_cum,
        "bench_cum": bench_cum,
        "annual_return": port_annual_return,
        "annual_vol": port_annual_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "correlation": corr,
        "sectors": sectors,
        "tickers": list(df.columns),
        "weights": w.tolist(),
        "individual_returns": {t: ((1 + df[t]).cumprod().iloc[-1] - 1) for t in df.columns},
    }


def layout():
    """Return the portfolio tracker layout."""
    return html.Div([
        html.Div("PORTFOLIO TRACKER", style={
            "fontSize": "11px", "color": COLORS["accent"],
            "letterSpacing": "2px", "marginBottom": "8px", "fontWeight": "bold",
        }),

        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Tickers", style={
                        "backgroundColor": COLORS["accent"], "color": "#000",
                        "fontWeight": "bold", "fontSize": "11px",
                    }),
                    dbc.Input(
                        id="portfolio-tickers",
                        value="AAPL, MSFT, GOOGL, AMZN, NVDA",
                        placeholder="AAPL, MSFT, GOOGL...",
                        style={"backgroundColor": COLORS["input_bg"], "color": COLORS["text"],
                               "border": f"1px solid {COLORS['border']}", "fontFamily": "monospace"},
                        debounce=True,
                    ),
                ], size="sm"),
            ], md=5),
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Weights", style={
                        "backgroundColor": COLORS["card_bg"], "color": COLORS["text"],
                        "fontSize": "11px", "border": f"1px solid {COLORS['border']}",
                    }),
                    dbc.Input(
                        id="portfolio-weights",
                        value="20, 20, 20, 20, 20",
                        placeholder="Equal weights by default",
                        style={"backgroundColor": COLORS["input_bg"], "color": COLORS["text"],
                               "border": f"1px solid {COLORS['border']}", "fontFamily": "monospace"},
                        debounce=True,
                    ),
                ], size="sm"),
            ], md=4),
            dbc.Col([
                dbc.Select(
                    id="portfolio-period",
                    options=[
                        {"label": "1M", "value": "1mo"},
                        {"label": "3M", "value": "3mo"},
                        {"label": "6M", "value": "6mo"},
                        {"label": "1Y", "value": "1y"},
                        {"label": "3Y", "value": "3y"},
                        {"label": "5Y", "value": "5y"},
                    ],
                    value="1y",
                    style={"backgroundColor": COLORS["input_bg"], "color": COLORS["text"],
                           "border": f"1px solid {COLORS['border']}", "fontSize": "11px"},
                ),
            ], md=2),
        ], className="mb-3"),

        # Metrics row
        dbc.Row(id="portfolio-metrics-row", className="mb-3"),

        # Charts
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="portfolio-perf-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=7),
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="portfolio-sector-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=5),
        ]),

        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="portfolio-corr-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=6),
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="portfolio-attribution-chart", config={"displayModeBar": False}),
                    type="dot", color=COLORS["accent"],
                ),
            ], md=6),
        ]),
    ])


def register_callbacks(app):
    @app.callback(
        [Output("portfolio-metrics-row", "children"),
         Output("portfolio-perf-chart", "figure"),
         Output("portfolio-sector-chart", "figure"),
         Output("portfolio-corr-chart", "figure"),
         Output("portfolio-attribution-chart", "figure")],
        [Input("portfolio-tickers", "value"),
         Input("portfolio-weights", "value"),
         Input("portfolio-period", "value")],
    )
    def update_portfolio(tickers_str, weights_str, period):
        if not tickers_str:
            empty = go.Figure()
            empty.update_layout(**chart_layout("Enter tickers above", height=300))
            return [], empty, empty, empty, empty

        tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
        try:
            weights = [float(w.strip()) for w in weights_str.split(",") if w.strip()]
        except (ValueError, AttributeError):
            weights = [1.0] * len(tickers)

        # Pad/trim weights
        while len(weights) < len(tickers):
            weights.append(weights[-1] if weights else 1.0)
        weights = weights[:len(tickers)]

        metrics = _compute_portfolio_metrics(tickers, weights, period)
        if metrics is None:
            empty = go.Figure()
            empty.update_layout(**chart_layout("No data available", height=300))
            return [], empty, empty, empty, empty

        # Metric cards
        def _metric_card(label, value, is_pct=True):
            color = change_color(value) if value else COLORS["text"]
            display = fmt_pct(value * 100) if is_pct and value else (fmt_price(value) if value else "—")
            return dbc.Col(html.Div([
                html.Div(label, style={"fontSize": "9px", "color": COLORS["accent"], "textTransform": "uppercase"}),
                html.Div(display, style={"fontSize": "18px", "fontWeight": "bold", "color": color, "fontFamily": "monospace"}),
            ], style={"padding": "8px", "backgroundColor": COLORS["card_bg"], "border": f"1px solid {COLORS['border']}", "borderRadius": "2px", "textAlign": "center"}),
                md=3, sm=6, className="mb-2")

        metric_cards = [
            _metric_card("Ann. Return", metrics["annual_return"]),
            _metric_card("Ann. Vol", metrics["annual_vol"]),
            _metric_card("Sharpe Ratio", metrics["sharpe"], is_pct=False),
            _metric_card("Max Drawdown", metrics["max_drawdown"]),
        ]

        # Performance chart
        perf_fig = go.Figure()
        perf_fig.add_trace(go.Scatter(
            x=metrics["port_cum"].index, y=metrics["port_cum"].values * 100,
            mode="lines", name="Portfolio",
            line={"color": COLORS["accent"], "width": 2},
        ))
        if not metrics["bench_cum"].empty:
            perf_fig.add_trace(go.Scatter(
                x=metrics["bench_cum"].index, y=metrics["bench_cum"].values * 100,
                mode="lines", name="SPY Benchmark",
                line={"color": COLORS["text_muted"], "width": 1, "dash": "dash"},
            ))
        perf_fig.update_layout(**chart_layout("PORTFOLIO vs BENCHMARK (SPY)", height=320))
        perf_fig.update_yaxes(title_text="Cumulative Return %")

        # Sector pie
        sector_fig = go.Figure()
        if metrics["sectors"]:
            sector_fig.add_trace(go.Pie(
                labels=list(metrics["sectors"].keys()),
                values=[v * 100 for v in metrics["sectors"].values()],
                hole=0.4,
                marker={"colors": [COLORS["accent"], COLORS["blue"], COLORS["cyan"],
                                   COLORS["green"], COLORS["red"], COLORS["accent_secondary"]]},
                textfont={"size": 10, "color": COLORS["text"]},
            ))
        sector_fig.update_layout(**chart_layout("SECTOR EXPOSURE", height=320))

        # Correlation heatmap
        corr = metrics["correlation"]
        corr_fig = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.index,
            colorscale=[[0, COLORS["blue"]], [0.5, COLORS["card_bg"]], [1, COLORS["red"]]],
            zmin=-1, zmax=1,
            text=np.round(corr.values, 2),
            texttemplate="%{text}",
            textfont={"size": 10},
        ))
        corr_fig.update_layout(**chart_layout("CORRELATION MATRIX", height=320))

        # Attribution bar chart
        attr_fig = go.Figure()
        indiv = metrics["individual_returns"]
        attr_fig.add_trace(go.Bar(
            x=list(indiv.keys()),
            y=[v * 100 for v in indiv.values()],
            marker_color=[COLORS["green"] if v >= 0 else COLORS["red"] for v in indiv.values()],
            text=[f"{v*100:.1f}%" for v in indiv.values()],
            textposition="outside",
            textfont={"size": 10, "color": COLORS["text"]},
        ))
        attr_fig.update_layout(**chart_layout("RETURNS BY HOLDING", height=320))
        attr_fig.update_yaxes(title_text="Return %")

        return metric_cards, perf_fig, sector_fig, corr_fig, attr_fig
