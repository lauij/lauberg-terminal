"""
Lauberg Terminal — Bloomberg-inspired Financial Dashboard
==========================================================

A professional, data-dense financial analytics dashboard built with
Dash/Plotly, yfinance, and FRED data. Dark theme, keyboard navigation,
multi-panel Bloomberg-style layout.

Usage:
    python app.py
    -> Opens at http://127.0.0.1:8050
"""

import logging
from datetime import datetime

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc

from dashboard.config import COLORS, HOST, PORT
from dashboard.panels import market_overview, equity, macro, portfolio, fx_commodities, screener, news

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    title="LAUBERG TERMINAL",
    update_title="LAUBERG | Loading...",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

server = app.server

# ─── Layout ──────────────────────────────────────────────────────────────────

app.layout = html.Div([
    # Hidden interval for status bar clock
    dcc.Interval(id="clock-interval", interval=10_000, n_intervals=0),

    # Header bar
    html.Div([
        html.Div([
            html.Span("LAUBERG", style={
                "fontSize": "16px", "fontWeight": "bold",
                "color": COLORS["accent"], "letterSpacing": "3px",
            }),
            html.Span(" TERMINAL", style={
                "fontSize": "16px", "fontWeight": "300",
                "color": COLORS["text"], "letterSpacing": "3px",
            }),
            html.Span("_", className="terminal-cursor", style={"fontSize": "16px"}),
        ], style={"display": "inline-block"}),
        html.Div([
            html.Span("F1", className="kbd"), html.Span(" Equity  ", style={"fontSize": "9px", "color": COLORS["text_muted"]}),
            html.Span("F2", className="kbd"), html.Span(" Macro  ", style={"fontSize": "9px", "color": COLORS["text_muted"]}),
            html.Span("F3", className="kbd"), html.Span(" Portfolio  ", style={"fontSize": "9px", "color": COLORS["text_muted"]}),
            html.Span("F4", className="kbd"), html.Span(" FX/Comm  ", style={"fontSize": "9px", "color": COLORS["text_muted"]}),
            html.Span("F5", className="kbd"), html.Span(" Screen  ", style={"fontSize": "9px", "color": COLORS["text_muted"]}),
            html.Span("F6", className="kbd"), html.Span(" News", style={"fontSize": "9px", "color": COLORS["text_muted"]}),
        ], style={"display": "inline-block", "float": "right", "marginTop": "4px"}),
    ], style={
        "backgroundColor": COLORS["header_bg"],
        "padding": "8px 16px",
        "borderBottom": f"1px solid {COLORS['border']}",
    }),

    # Market overview ticker bar
    market_overview.layout(),

    # Main content tabs
    dbc.Tabs([
        dbc.Tab(
            html.Div(equity.layout(), className="panel-content"),
            label="EQUITY",
            tab_id="tab-equity",
            tab_style={"marginLeft": "0"},
        ),
        dbc.Tab(
            html.Div(macro.layout(), className="panel-content"),
            label="MACRO",
            tab_id="tab-macro",
        ),
        dbc.Tab(
            html.Div(portfolio.layout(), className="panel-content"),
            label="PORTFOLIO",
            tab_id="tab-portfolio",
        ),
        dbc.Tab(
            html.Div(fx_commodities.layout(), className="panel-content"),
            label="FX / COMM",
            tab_id="tab-fxcomm",
        ),
        dbc.Tab(
            html.Div(screener.layout(), className="panel-content"),
            label="SCREENER",
            tab_id="tab-screener",
        ),
        dbc.Tab(
            html.Div(news.layout(), className="panel-content"),
            label="NEWS",
            tab_id="tab-news",
        ),
    ], id="main-tabs", active_tab="tab-equity"),

    # Status bar
    html.Div([
        html.Div([
            html.Span(className="status-dot online"),
            html.Span(" CONNECTED", style={"color": COLORS["green"]}),
        ], className="status-item"),
        html.Div([
            html.Span("DATA: "),
            html.Span("yfinance + FRED", style={"color": COLORS["text"]}),
        ], className="status-item"),
        html.Div([
            html.Span("CACHE: "),
            html.Span("SQLite", style={"color": COLORS["text"]}),
        ], className="status-item"),
        html.Div(id="status-clock", style={"marginLeft": "auto"}),
    ], className="status-bar"),

    # Keyboard navigation handler
    html.Div(id="keyboard-handler", style={"display": "none"}),
], style={"backgroundColor": COLORS["bg"], "minHeight": "100vh"})

# ─── Register all panel callbacks ────────────────────────────────────────────

market_overview.register_callbacks(app)
equity.register_callbacks(app)
macro.register_callbacks(app)
portfolio.register_callbacks(app)
fx_commodities.register_callbacks(app)
screener.register_callbacks(app)
news.register_callbacks(app)


# ─── App-level callbacks ─────────────────────────────────────────────────────

@app.callback(
    Output("status-clock", "children"),
    Input("clock-interval", "n_intervals"),
)
def update_clock(_n):
    now = datetime.now()
    return html.Span([
        html.Span("LAST REFRESH: ", style={"color": COLORS["text_muted"]}),
        html.Span(now.strftime("%H:%M:%S"), style={"color": COLORS["accent"]}),
        html.Span(f"  {now.strftime('%Y-%m-%d')}", style={"color": COLORS["text_muted"]}),
    ])


# Add keyboard navigation via clientside callback
app.clientside_callback(
    """
    function(n) {
        document.addEventListener('keydown', function(e) {
            const tabMap = {
                'F1': 'tab-equity',
                'F2': 'tab-macro',
                'F3': 'tab-portfolio',
                'F4': 'tab-fxcomm',
                'F5': 'tab-screener',
                'F6': 'tab-news',
            };
            if (tabMap[e.key]) {
                e.preventDefault();
                // Find and click the correct tab
                const tabs = document.querySelectorAll('.nav-tabs .nav-link');
                const tabNames = ['tab-equity', 'tab-macro', 'tab-portfolio', 'tab-fxcomm', 'tab-screener', 'tab-news'];
                const idx = tabNames.indexOf(tabMap[e.key]);
                if (idx >= 0 && tabs[idx]) {
                    tabs[idx].click();
                }
            }
        });
        return window.dash_clientside.no_update;
    }
    """,
    Output("keyboard-handler", "children"),
    Input("clock-interval", "n_intervals"),
)


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(f"Starting Lauberg Terminal on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
