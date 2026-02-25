"""
Configuration constants for the Global Portfolio One replication.
Based on Dr. Andreas Beck's Equal-Value-Index methodology.
"""

# --------------------------------------------------------------------------- #
# Equal-Value Regional Weights (% of equity sleeve)
# Derived from the report's target allocations as of July 2025
# --------------------------------------------------------------------------- #
EQUITY_WEIGHTS = {
    "north_america": 0.4848,
    "europe":        0.1615,
    "emerging_markets": 0.0814,
    "small_caps":    0.0777,
    "japan":         0.0587,
    "pacific_ex_jp": 0.0175,
}

# --------------------------------------------------------------------------- #
# Regime Definitions
# --------------------------------------------------------------------------- #
REGIME_A_EQUITY = 0.80
REGIME_A_RESERVE = 0.20

REGIME_B_EQUITY = 0.90
REGIME_B_RESERVE = 0.10

REGIME_C_EQUITY = 1.00
REGIME_C_RESERVE = 0.00

# Drawdown triggers (from All-Time High)
REGIME_B_DRAWDOWN_TRIGGER = -0.20   # -20 %
REGIME_C_DRAWDOWN_TRIGGER = -0.40   # -40 %

# Credit spread thresholds (OAS in percentage points)
SPREAD_ELEVATED = 2.50   # BBB OAS above this = elevated
SPREAD_EXTREME  = 4.50   # BBB OAS above this = extreme

# Recovery triggers
RECOVERY_C_TO_B_RALLY = 0.50   # +50 % from trough
RECOVERY_B_TO_A_RALLY = 0.25   # additional +25 %

# --------------------------------------------------------------------------- #
# Reserve Composition (% of reserve sleeve)
# --------------------------------------------------------------------------- #
RESERVE_WEIGHTS = {
    "inflation_linked": 0.50,
    "money_market":     0.40,
    "gold":             0.05,
    "cash":             0.05,
}

# --------------------------------------------------------------------------- #
# ETF Universe – UCITS compliant
# --------------------------------------------------------------------------- #
ETFS = {
    "north_america": {
        "name": "iShares Core S&P 500 UCITS ETF",
        "isin": "IE00B5BMR087",
        "ticker": "SXR8.DE",
        "ter": 0.0007,
        "index": "S&P 500",
    },
    "europe": {
        "name": "Lyxor Core STOXX Europe 600 UCITS ETF",
        "isin": "LU0908500753",
        "ticker": "MEUD.PA",
        "ter": 0.0007,
        "index": "STOXX Europe 600",
    },
    "emerging_markets": {
        "name": "iShares Core MSCI EM IMI UCITS ETF",
        "isin": "IE00BKM4GZ66",
        "ticker": "IS3N.DE",
        "ter": 0.0018,
        "index": "MSCI EM IMI",
    },
    "small_caps": {
        "name": "iShares MSCI World Small Cap UCITS ETF",
        "isin": "IE00BF4RFH31",
        "ticker": "IUSN.DE",
        "ter": 0.0035,
        "index": "MSCI World Small Cap",
    },
    "japan": {
        "name": "Amundi Prime Japan UCITS ETF",
        "isin": "LU1931974775",
        "ticker": "PRIJ.DE",
        "ter": 0.0005,
        "index": "MSCI Japan",
    },
    "pacific_ex_jp": {
        "name": "iShares MSCI Pacific ex-Japan UCITS ETF",
        "isin": "IE00B52MJY50",
        "ticker": "IQQP.DE",
        "ter": 0.0020,
        "index": "MSCI Pacific ex-Japan",
    },
    "inflation_linked": {
        "name": "iShares Euro Inflation Linked Govt Bond UCITS ETF",
        "isin": "IE00B0M62X26",
        "ticker": "IBCI.DE",
        "ter": 0.0020,
        "index": "Bloomberg Euro Govt Inflation-Linked",
    },
    "money_market": {
        "name": "Xtrackers II EUR Overnight Rate Swap UCITS ETF",
        "isin": "LU0290358497",
        "ticker": "XEON.DE",
        "ter": 0.0010,
        "index": "EUR Overnight Rate",
    },
    "gold": {
        "name": "Xtrackers IE Physical Gold ETC",
        "isin": "DE000A2T0VU5",
        "ticker": "XAD5.DE",
        "ter": 0.0015,
        "index": "Gold Spot",
    },
}

# Simplified 3-ETF model
SIMPLE_ETFS = {
    "acwi_imi": {
        "name": "SPDR MSCI ACWI IMI UCITS ETF",
        "isin": "IE00B3YLTY66",
        "ticker": "SPYI.DE",
        "ter": 0.0017,
        "weight": 0.70,
    },
    "small_caps": {
        "name": "iShares MSCI World Small Cap UCITS ETF",
        "isin": "IE00BF4RFH31",
        "ticker": "IUSN.DE",
        "ter": 0.0035,
        "weight": 0.10,
    },
    "cash": {
        "name": "High-Yield Savings / Money Market",
        "isin": "N/A",
        "ticker": "N/A",
        "ter": 0.0,
        "weight": 0.20,
    },
}

# --------------------------------------------------------------------------- #
# Market data tickers for regime detection
# --------------------------------------------------------------------------- #
MSCI_WORLD_PROXY = "URTH"          # iShares MSCI World ETF (USD)
VIX_TICKER       = "^VIX"
SP500_TICKER     = "^GSPC"

# FRED series for credit spreads
FRED_SPREAD_SERIES = "BAMLC0A4CBBB"  # ICE BofA BBB US Corporate OAS
FRED_API_BASE      = "https://api.stlouisfed.org/fred/series/observations"
