"""
Global Portfolio One – Welt AG Replication Dashboard

A Flask application that implements the GPO strategy:
  • Equal-Value-Index regional weighting ("Welt AG")
  • Three-regime dynamic asset allocation
  • Anti-cyclical rebalancing protocol
"""

from __future__ import annotations

import dataclasses
import logging

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# Load local .env before importing modules that read env vars at import time.
load_dotenv()

from engine.allocator import compute_allocation
from engine.config import EQUITY_WEIGHTS, ETFS, RESERVE_WEIGHTS, SIMPLE_ETFS
from engine.market_data import fetch_dashboard_data
from engine.recovery import compute_recovery_levels
from engine.regime import detect_regime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------------------------------- #
# API: Market Data & Regime
# --------------------------------------------------------------------------- #
@app.route("/api/dashboard")
def api_dashboard():
    """Fetch live market data and compute the current regime."""
    try:
        data = fetch_dashboard_data()
        dd = data["drawdown"]["drawdown_pct"]
        vix = data["vix"]
        spread = data["credit_spread"]

        regime = detect_regime(dd, credit_spread=spread, vix=vix)

        recovery = compute_recovery_levels(
            current_regime=regime.regime,
            trough_price=data["drawdown"].get("trough"),
            current_price=data["drawdown"].get("current_price"),
            ath_price=data["drawdown"].get("ath"),
        )

        return jsonify({
            "market": data,
            "regime": dataclasses.asdict(regime),
            "recovery": dataclasses.asdict(recovery),
        })
    except Exception as exc:
        logger.exception("Dashboard API error")
        return jsonify({"error": str(exc)}), 500


# --------------------------------------------------------------------------- #
# API: Portfolio Allocation
# --------------------------------------------------------------------------- #
@app.route("/api/allocate", methods=["POST"])
def api_allocate():
    """
    Compute target allocations for a given portfolio value.
    Accepts JSON: { "portfolio_value": 100000, "current_holdings": {...} }
    """
    try:
        body = request.get_json(force=True)
        portfolio_value = float(body.get("portfolio_value", 100000))
        current_holdings = body.get("current_holdings", {})

        # Detect current regime from live data
        data = fetch_dashboard_data()
        dd = data["drawdown"]["drawdown_pct"]
        vix = data["vix"]
        spread = data["credit_spread"]
        regime = detect_regime(dd, credit_spread=spread, vix=vix)

        result = compute_allocation(portfolio_value, regime, current_holdings)

        return jsonify({
            "allocation": {
                "portfolio_value": result.portfolio_value,
                "regime": result.regime,
                "equity_pct": result.equity_pct,
                "reserve_pct": result.reserve_pct,
                "equity_value": round(result.equity_value, 2),
                "reserve_value": round(result.reserve_value, 2),
                "weighted_ter": result.weighted_ter,
                "rebalance_actions": result.rebalance_actions,
                "positions": [dataclasses.asdict(p) for p in result.positions],
                "simple_positions": [dataclasses.asdict(p) for p in result.simple_positions],
            }
        })
    except Exception as exc:
        logger.exception("Allocate API error")
        return jsonify({"error": str(exc)}), 500


# --------------------------------------------------------------------------- #
# API: Static Reference Data
# --------------------------------------------------------------------------- #
@app.route("/api/reference")
def api_reference():
    """Return the static configuration tables."""
    return jsonify({
        "equity_weights": EQUITY_WEIGHTS,
        "reserve_weights": RESERVE_WEIGHTS,
        "etfs": ETFS,
        "simple_etfs": SIMPLE_ETFS,
    })


# --------------------------------------------------------------------------- #
# API: Simulate regime for a hypothetical drawdown/spread
# --------------------------------------------------------------------------- #
@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """
    Simulate a regime for user-supplied drawdown and spread values.
    JSON: { "drawdown_pct": -25, "credit_spread": 3.5, "vix": 35, "portfolio_value": 100000 }
    """
    try:
        body = request.get_json(force=True)
        dd = float(body.get("drawdown_pct", 0))
        spread = body.get("credit_spread")
        vix = body.get("vix")
        pv = float(body.get("portfolio_value", 100000))

        if spread is not None:
            spread = float(spread)
        if vix is not None:
            vix = float(vix)

        regime = detect_regime(dd, credit_spread=spread, vix=vix)
        result = compute_allocation(pv, regime)

        return jsonify({
            "regime": dataclasses.asdict(regime),
            "allocation": {
                "portfolio_value": result.portfolio_value,
                "regime": result.regime,
                "equity_pct": result.equity_pct,
                "reserve_pct": result.reserve_pct,
                "equity_value": round(result.equity_value, 2),
                "reserve_value": round(result.reserve_value, 2),
                "weighted_ter": result.weighted_ter,
                "positions": [dataclasses.asdict(p) for p in result.positions],
                "simple_positions": [dataclasses.asdict(p) for p in result.simple_positions],
            },
        })
    except Exception as exc:
        logger.exception("Simulate API error")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
