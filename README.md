# Global Portfolio One – Welt AG Replication

A web application that replicates Dr. Andreas Beck's **Global Portfolio One (GPO)** investment strategy, implementing the "Welt AG" Equal-Value-Index approach with dynamic regime-based asset allocation.

## Features

- **Regime Dashboard** – Live market monitoring with drawdown tracking, VIX, and credit spread analysis. Automatically detects the current market regime (A/B/C) and displays target allocations.
- **Portfolio Allocator** – Enter your portfolio value to get exact EUR amounts for each ETF in both the Scientific (6-ETF) and Simplified (3-ETF) models.
- **Regime Simulator** – Test hypothetical crisis scenarios by adjusting drawdown, credit spreads, and VIX to see how the regime engine responds.
- **Reference Tables** – Complete ETF universe, regional weights, and regime switching rules.

## Strategy Overview

| Regime | Condition | Equity | Reserve |
|--------|-----------|--------|---------|
| **A** (Normal) | Drawdown < 20% or no credit stress | 80% | 20% |
| **B** (Equity Scarcity) | Drawdown ≥ 20% + elevated spreads/VIX | 90% | 10% |
| **C** (Escalation) | Drawdown ≥ 40% + extreme spreads/VIX | 100% | 0% |

The equity sleeve uses an **Equal-Value-Index** that underweights expensive regions (vs. market cap) and overweights cheaper ones, with dedicated small-cap exposure.

## Quick Start

```bash
pip install -r requirements.txt
python3 app.py
```

Open http://localhost:5000 in your browser.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `GPO_DEMO` | `1` | Use synthetic demo data when live feeds are unavailable |
| `FRED_API_KEY` | – | FRED API key for real credit spread data |

## Project Structure

```
├── app.py                  # Flask application & API routes
├── engine/
│   ├── config.py           # ETF universe, weights, thresholds
│   ├── regime.py           # Three-state regime detection
│   ├── allocator.py        # Portfolio allocation calculator
│   ├── recovery.py         # Recovery protocol (C→B→A)
│   └── market_data.py      # Market data fetching + demo fallback
├── templates/
│   └── index.html          # Dashboard UI
├── static/
│   ├── css/style.css       # Dark-themed responsive styles
│   └── js/app.js           # Frontend logic & canvas charts
├── tests/
│   └── test_engine.py      # 28 unit tests
└── requirements.txt
```

## Running Tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

## Production

```bash
gunicorn app:app --bind 0.0.0.0:8000 --workers 2
```
