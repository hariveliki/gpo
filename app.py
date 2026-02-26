"""
Global Portfolio One – Welt AG Replication Dashboard

A Flask application that implements the GPO strategy:
  • Equal-Value-Index regional weighting ("Welt AG")
  • Three-regime dynamic asset allocation
  • Anti-cyclical rebalancing protocol
"""

from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path

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

WEIGHTS_FILE = Path(__file__).parent / "weights.json"


def _load_saved_weights() -> dict | None:
    """Load user-saved weight overrides from disk, or None if not present."""
    if not WEIGHTS_FILE.exists():
        return None
    try:
        return json.loads(WEIGHTS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _get_effective_weights() -> tuple[dict, dict]:
    """Return (equity_weights, reserve_weights) respecting saved overrides."""
    saved = _load_saved_weights()
    if saved:
        eq = saved.get("equity_weights", EQUITY_WEIGHTS)
        res = saved.get("reserve_weights", RESERVE_WEIGHTS)
        return eq, res
    return dict(EQUITY_WEIGHTS), dict(RESERVE_WEIGHTS)


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
    Accepts JSON: { "portfolio_value": 100000, "current_holdings": {...},
                     "equity_weights": {...}, "reserve_weights": {...} }
    """
    try:
        body = request.get_json(force=True)
        portfolio_value = float(body.get("portfolio_value", 100000))
        current_holdings = body.get("current_holdings", {})
        custom_eq = body.get("equity_weights")
        custom_res = body.get("reserve_weights")

        if custom_eq:
            custom_eq = {k: float(v) for k, v in custom_eq.items()}
        if custom_res:
            custom_res = {k: float(v) for k, v in custom_res.items()}

        data = fetch_dashboard_data()
        dd = data["drawdown"]["drawdown_pct"]
        vix = data["vix"]
        spread = data["credit_spread"]
        regime = detect_regime(dd, credit_spread=spread, vix=vix)

        result = compute_allocation(
            portfolio_value, regime, current_holdings,
            equity_weights=custom_eq, reserve_weights=custom_res,
        )

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
    """Return configuration tables, including any saved weight overrides."""
    eff_eq, eff_res = _get_effective_weights()
    has_saved = _load_saved_weights() is not None
    return jsonify({
        "equity_weights": eff_eq,
        "reserve_weights": eff_res,
        "original_equity_weights": EQUITY_WEIGHTS,
        "original_reserve_weights": RESERVE_WEIGHTS,
        "has_saved_defaults": has_saved,
        "etfs": ETFS,
        "simple_etfs": SIMPLE_ETFS,
    })


# --------------------------------------------------------------------------- #
# API: Save / Restore Default Weights
# --------------------------------------------------------------------------- #
@app.route("/api/weights", methods=["POST"])
def api_save_weights():
    """
    Persist custom weights as the new defaults.
    JSON: { "equity_weights": {...}, "reserve_weights": {...} }
    """
    try:
        body = request.get_json(force=True)
        eq = body.get("equity_weights")
        res = body.get("reserve_weights")

        if not eq and not res:
            return jsonify({"error": "Provide equity_weights and/or reserve_weights"}), 400

        saved = _load_saved_weights() or {}
        if eq:
            saved["equity_weights"] = {k: float(v) for k, v in eq.items()}
        if res:
            saved["reserve_weights"] = {k: float(v) for k, v in res.items()}

        WEIGHTS_FILE.write_text(json.dumps(saved, indent=2))
        logger.info("Saved custom default weights to %s", WEIGHTS_FILE)
        return jsonify({"ok": True})
    except Exception as exc:
        logger.exception("Save weights error")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/weights", methods=["DELETE"])
def api_delete_weights():
    """Remove saved weight overrides, restoring original config defaults."""
    try:
        if WEIGHTS_FILE.exists():
            WEIGHTS_FILE.unlink()
            logger.info("Deleted saved weights file %s", WEIGHTS_FILE)
        return jsonify({"ok": True})
    except Exception as exc:
        logger.exception("Delete weights error")
        return jsonify({"error": str(exc)}), 500


# --------------------------------------------------------------------------- #
# API: Simulate regime for a hypothetical drawdown/spread
# --------------------------------------------------------------------------- #
@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """
    Simulate a regime for user-supplied drawdown and spread values.
    JSON: { "drawdown_pct": -25, "credit_spread": 3.5, "vix": 35,
            "portfolio_value": 100000, "equity_weights": {...}, "reserve_weights": {...} }
    """
    try:
        body = request.get_json(force=True)
        dd = float(body.get("drawdown_pct", 0))
        spread = body.get("credit_spread")
        vix = body.get("vix")
        pv = float(body.get("portfolio_value", 100000))
        custom_eq = body.get("equity_weights")
        custom_res = body.get("reserve_weights")

        if spread is not None:
            spread = float(spread)
        if vix is not None:
            vix = float(vix)
        if custom_eq:
            custom_eq = {k: float(v) for k, v in custom_eq.items()}
        if custom_res:
            custom_res = {k: float(v) for k, v in custom_res.items()}

        regime = detect_regime(dd, credit_spread=spread, vix=vix)
        result = compute_allocation(
            pv, regime,
            equity_weights=custom_eq, reserve_weights=custom_res,
        )

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
