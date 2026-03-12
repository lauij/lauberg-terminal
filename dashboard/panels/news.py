"""News Feed Panel — aggregated news from yfinance."""

from datetime import datetime

from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc

from dashboard.config import COLORS
from dashboard.data.market import get_news


DEFAULT_TICKERS = ["SPY", "AAPL", "MSFT", "GOOGL", "TSLA", "BTC-USD", "CL=F", "GC=F"]

TOPIC_TICKERS = {
    "All": DEFAULT_TICKERS,
    "Tech": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN"],
    "Energy": ["XLE", "CL=F", "BZ=F", "NG=F"],
    "Macro": ["SPY", "^TNX", "GC=F", "EURUSD=X", "DX-Y.NYB"],
    "Crypto": ["BTC-USD", "ETH-USD"],
}


def _format_news_item(item: dict, ticker: str) -> html.Div:
    """Format a single news item."""
    ts = item.get("providerPublishTime", 0)
    dt = datetime.fromtimestamp(ts).strftime("%b %d, %H:%M") if ts else ""
    publisher = item.get("publisher", "")

    return html.Div([
        html.Div([
            html.Span(ticker, style={
                "backgroundColor": COLORS["accent"],
                "color": "#000",
                "padding": "1px 6px",
                "fontSize": "9px",
                "fontWeight": "bold",
                "marginRight": "8px",
                "borderRadius": "2px",
            }),
            html.Span(f"{publisher} · {dt}", style={
                "color": COLORS["text_muted"],
                "fontSize": "9px",
            }),
        ], style={"marginBottom": "2px"}),
        html.A(
            item.get("title", "No title"),
            href=item.get("link", "#"),
            target="_blank",
            style={
                "color": COLORS["text"],
                "fontSize": "12px",
                "textDecoration": "none",
                "lineHeight": "1.3",
            },
        ),
    ], style={
        "padding": "8px 12px",
        "borderBottom": f"1px solid {COLORS['border']}",
    })


def layout():
    """Return the news feed layout."""
    return html.Div([
        html.Div("NEWS FEED", style={
            "fontSize": "11px", "color": COLORS["accent"],
            "letterSpacing": "2px", "marginBottom": "8px", "fontWeight": "bold",
        }),

        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(topic, id=f"news-topic-{topic}", size="sm",
                               outline=True, color="warning",
                               className="px-3", style={"fontSize": "10px"})
                    for topic in TOPIC_TICKERS.keys()
                ]),
            ], width="auto"),
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("TICKER", style={
                        "backgroundColor": COLORS["card_bg"], "color": COLORS["text"],
                        "fontSize": "11px", "border": f"1px solid {COLORS['border']}",
                    }),
                    dbc.Input(
                        id="news-custom-ticker",
                        placeholder="Custom ticker...",
                        style={"backgroundColor": COLORS["input_bg"], "color": COLORS["text"],
                               "border": f"1px solid {COLORS['border']}", "fontFamily": "monospace"},
                        debounce=True,
                    ),
                ], size="sm"),
            ], md=3),
        ], className="mb-3 align-items-center"),

        dcc.Loading(
            html.Div(
                id="news-feed-container",
                style={
                    "maxHeight": "600px",
                    "overflowY": "auto",
                    "backgroundColor": COLORS["card_bg"],
                    "border": f"1px solid {COLORS['border']}",
                    "borderRadius": "2px",
                },
            ),
            type="dot",
            color=COLORS["accent"],
        ),

        dcc.Interval(id="news-interval", interval=300_000, n_intervals=0),
    ])


def register_callbacks(app):
    @app.callback(
        Output("news-feed-container", "children"),
        [Input(f"news-topic-{topic}", "n_clicks") for topic in TOPIC_TICKERS.keys()],
        Input("news-custom-ticker", "value"),
        Input("news-interval", "n_intervals"),
    )
    def update_news(*args):
        from dash import ctx

        custom_ticker = args[-2]
        topic_tickers = DEFAULT_TICKERS

        if custom_ticker and custom_ticker.strip():
            topic_tickers = [custom_ticker.strip().upper()]
        elif ctx.triggered_id:
            for topic, tickers in TOPIC_TICKERS.items():
                if ctx.triggered_id == f"news-topic-{topic}":
                    topic_tickers = tickers
                    break

        # Aggregate news from all tickers
        all_news = []
        for t in topic_tickers:
            news = get_news(t)
            for item in news:
                item["_ticker"] = t
                all_news.append(item)

        # Sort by publish time (descending)
        all_news.sort(key=lambda x: x.get("providerPublishTime", 0), reverse=True)

        # Deduplicate by title
        seen_titles = set()
        unique_news = []
        for item in all_news:
            title = item.get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(item)

        if not unique_news:
            return html.Div("No news available", style={
                "color": COLORS["text_muted"], "padding": "20px", "textAlign": "center",
            })

        return [_format_news_item(item, item.get("_ticker", "")) for item in unique_news[:50]]
