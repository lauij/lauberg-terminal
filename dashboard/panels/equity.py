"""Equity Deep-Dive Panel — price charts, fundamentals, news."""

from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.config import COLORS
from dashboard.data.market import get_history, get_ticker_info, get_news
from dashboard.utils.formatting import (
    fmt_price, fmt_pct, fmt_large_number, chart_layout, change_color,
)


def _build_price_chart(ticker: str, period: str) -> go.Figure:
    """Build a candlestick + volume chart with moving averages."""
    interval = "5m" if period == "1d" else "1d"
    df = get_history(ticker, period=period, interval=interval)

    if df.empty:
        fig = go.Figure()
        fig.update_layout(**chart_layout(f"No data for {ticker}", height=450))
        return fig

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color=COLORS["green"],
            decreasing_line_color=COLORS["red"],
            name="Price",
        ),
        row=1, col=1,
    )

    # Moving averages (only for periods with enough data)
    if len(df) >= 50:
        ma50 = df["Close"].rolling(50).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=ma50,
                line={"color": COLORS["accent"], "width": 1},
                name="MA50",
            ),
            row=1, col=1,
        )
    if len(df) >= 200:
        ma200 = df["Close"].rolling(200).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=ma200,
                line={"color": COLORS["cyan"], "width": 1},
                name="MA200",
            ),
            row=1, col=1,
        )

    # Volume bars
    colors = [
        COLORS["green"] if c >= o else COLORS["red"]
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(
        go.Bar(
            x=df.index, y=df["Volume"],
            marker_color=colors,
            opacity=0.5,
            name="Volume",
            showlegend=False,
        ),
        row=2, col=1,
    )

    fig.update_layout(
        **chart_layout(f"{ticker.upper()} — {period.upper()}", height=450),
        xaxis_rangeslider_visible=False,
        showlegend=True,
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Vol", row=2, col=1)

    return fig


def _stat_row(label: str, value, is_pct=False, is_money=False) -> html.Tr:
    """Create a row in the stats table."""
    if value is None:
        display = "—"
        color = COLORS["text_muted"]
    elif is_pct:
        display = fmt_pct(value * 100 if abs(value) < 1 else value)
        color = change_color(value)
    elif is_money:
        display = fmt_large_number(value)
        color = COLORS["text"]
    else:
        display = fmt_price(value)
        color = COLORS["text"]

    return html.Tr([
        html.Td(label, style={"color": COLORS["text_muted"], "fontSize": "11px", "padding": "3px 8px"}),
        html.Td(display, style={"color": color, "fontSize": "11px", "textAlign": "right", "padding": "3px 8px", "fontFamily": "monospace"}),
    ])


def layout():
    """Return the equity deep-dive panel layout."""
    return html.Div([
        # Ticker input bar
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText(
                        "EQUITY",
                        style={"backgroundColor": COLORS["accent"], "color": "#000", "fontWeight": "bold", "fontSize": "11px"},
                    ),
                    dbc.Input(
                        id="equity-ticker-input",
                        value="AAPL",
                        placeholder="Enter ticker...",
                        style={"backgroundColor": COLORS["input_bg"], "color": COLORS["text"], "border": f"1px solid {COLORS['border']}", "fontFamily": "monospace"},
                        debounce=True,
                    ),
                ], size="sm"),
            ], width=3),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(p, id=f"eq-period-{p}", size="sm", outline=True, color="warning",
                               className="px-2", style={"fontSize": "10px"})
                    for p in ["1d", "5d", "1mo", "3mo", "1y", "5y"]
                ]),
            ], width="auto"),
        ], className="mb-2 align-items-center"),

        dbc.Row([
            # Chart area
            dbc.Col([
                dcc.Loading(
                    dcc.Graph(id="equity-chart", config={"displayModeBar": False}),
                    type="dot",
                    color=COLORS["accent"],
                ),
            ], md=8),

            # Stats + news sidebar
            dbc.Col([
                html.Div(id="equity-stats-panel"),
                html.Hr(style={"borderColor": COLORS["border"]}),
                html.Div(
                    "ANALYST TARGETS",
                    style={"fontSize": "10px", "color": COLORS["accent"], "letterSpacing": "1px", "marginBottom": "4px"},
                ),
                html.Div(id="equity-targets-panel"),
                html.Hr(style={"borderColor": COLORS["border"]}),
                html.Div(
                    "NEWS",
                    style={"fontSize": "10px", "color": COLORS["accent"], "letterSpacing": "1px", "marginBottom": "4px"},
                ),
                html.Div(
                    id="equity-news-panel",
                    style={"maxHeight": "200px", "overflowY": "auto"},
                ),
            ], md=4),
        ]),
    ])


def register_callbacks(app):
    # Store selected period
    @app.callback(
        Output("equity-chart", "figure"),
        Input("equity-ticker-input", "value"),
        [Input(f"eq-period-{p}", "n_clicks") for p in ["1d", "5d", "1mo", "3mo", "1y", "5y"]],
    )
    def update_chart(ticker, *period_clicks):
        if not ticker:
            return no_update

        from dash import ctx
        periods = ["1d", "5d", "1mo", "3mo", "1y", "5y"]
        period = "1y"  # default
        if ctx.triggered_id and ctx.triggered_id.startswith("eq-period-"):
            period = ctx.triggered_id.replace("eq-period-", "")

        return _build_price_chart(ticker.strip().upper(), period)

    @app.callback(
        [Output("equity-stats-panel", "children"),
         Output("equity-targets-panel", "children"),
         Output("equity-news-panel", "children")],
        Input("equity-ticker-input", "value"),
    )
    def update_info(ticker):
        if not ticker:
            return no_update, no_update, no_update

        ticker = ticker.strip().upper()
        info = get_ticker_info(ticker)
        news = get_news(ticker)

        # Stats table
        stats_table = html.Table([
            html.Tbody([
                _stat_row("Market Cap", info.get("marketCap"), is_money=True),
                _stat_row("EV", info.get("enterpriseValue"), is_money=True),
                _stat_row("P/E (TTM)", info.get("trailingPE")),
                _stat_row("P/E (FWD)", info.get("forwardPE")),
                _stat_row("EV/EBITDA", info.get("enterpriseToEbitda")),
                _stat_row("PEG", info.get("pegRatio")),
                _stat_row("P/B", info.get("priceToBook")),
                _stat_row("Rev Growth", info.get("revenueGrowth"), is_pct=True),
                _stat_row("Gross Margin", info.get("grossMargins"), is_pct=True),
                _stat_row("Op Margin", info.get("operatingMargins"), is_pct=True),
                _stat_row("Net Margin", info.get("profitMargins"), is_pct=True),
                _stat_row("ROE", info.get("returnOnEquity"), is_pct=True),
                _stat_row("Beta", info.get("beta")),
                _stat_row("Div Yield", info.get("dividendYield"), is_pct=True),
                _stat_row("52W High", info.get("fiftyTwoWeekHigh")),
                _stat_row("52W Low", info.get("fiftyTwoWeekLow")),
            ])
        ], style={"width": "100%", "borderCollapse": "collapse"})

        # Analyst targets
        targets = html.Div([
            html.Span(f"Low: {fmt_price(info.get('targetLowPrice'))}  ", style={"color": COLORS["red"], "fontSize": "11px"}),
            html.Span(f"Mean: {fmt_price(info.get('targetMeanPrice'))}  ", style={"color": COLORS["accent"], "fontSize": "11px", "fontWeight": "bold"}),
            html.Span(f"High: {fmt_price(info.get('targetHighPrice'))}", style={"color": COLORS["green"], "fontSize": "11px"}),
            html.Br(),
            html.Span(
                f"Consensus: {info.get('recommendationKey', '—').upper()} ({info.get('numberOfAnalystOpinions', '—')} analysts)",
                style={"color": COLORS["text_muted"], "fontSize": "10px"},
            ),
        ])

        # News
        news_items = []
        for n in news[:8]:
            from datetime import datetime
            ts = n.get("providerPublishTime", 0)
            dt = datetime.fromtimestamp(ts).strftime("%m/%d %H:%M") if ts else ""
            news_items.append(
                html.Div([
                    html.A(
                        n.get("title", ""),
                        href=n.get("link", "#"),
                        target="_blank",
                        style={"color": COLORS["blue"], "fontSize": "11px", "textDecoration": "none"},
                    ),
                    html.Span(f"  {n.get('publisher', '')} · {dt}",
                              style={"color": COLORS["text_muted"], "fontSize": "9px"}),
                ], style={"marginBottom": "6px"})
            )

        return stats_table, targets, html.Div(news_items) if news_items else html.Div("No news available", style={"color": COLORS["text_muted"], "fontSize": "11px"})
