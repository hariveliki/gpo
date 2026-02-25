# Financial Data Methodologies — Detailed Answers

This document answers seven questions about how the GPO replication engine sources, calculates, and uses its financial data.

---

## 1. How is the MSCI World proxy calculated?

The application does **not** calculate the MSCI World index from its constituents. Instead, it uses a **proxy ETF** — the iShares MSCI World ETF, traded in the US under ticker **`URTH`** — as a stand-in for the MSCI World Index.

**Configuration** (`engine/config.py`, line 150):

```python
MSCI_WORLD_PROXY = "URTH"          # iShares MSCI World ETF (USD)
```

**Data retrieval** (`engine/market_data.py`, lines 50–75):

The function `fetch_index_history()` downloads the daily closing-price history of `URTH` (default ticker) via the `yfinance` library:

```python
def fetch_index_history(
    ticker: str = MSCI_WORLD_PROXY,
    period: str = "5y",
    interval: str = "1d",
) -> pd.DataFrame:
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    df = data[["Close"]].copy()
    df.columns = ["close"]
    ...
```

The returned `close` column is then used to compute drawdown from the all-time high (ATH), which is the primary input for regime detection.

**Why URTH?** — URTH is an NYSE-listed iShares ETF that tracks the MSCI World Index. Its daily close prices closely mirror the index, making it a practical, freely available proxy that can be fetched in real time through Yahoo Finance without requiring a paid MSCI data subscription.

---

## 2. How is the VIX (Fear Index) calculated?

The application does **not** compute the VIX from options prices. It fetches the **pre-calculated VIX closing value** directly from Yahoo Finance using ticker **`^VIX`**.

**Configuration** (`engine/config.py`, line 151):

```python
VIX_TICKER = "^VIX"
```

**Data retrieval** (`engine/market_data.py`, lines 121–138):

```python
def fetch_vix() -> Optional[float]:
    data = yf.download(VIX_TICKER, period="5d", interval="1d", progress=False)
    val = float(data["Close"].dropna().iloc[-1])
    return round(val, 2)
```

The function downloads the last 5 trading days of VIX data and returns the most recent close. This value is cached for 30 minutes to avoid redundant API calls.

**How the VIX is used**: A VIX value ≥ 30 is treated as a **stress confirmation signal** (`engine/regime.py`, lines 80–82). It acts as an alternative (or complement) to the credit spread for confirming that a market drawdown reflects genuine stress rather than a normal pullback.

---

## 3. How is the Credit Spread (BBB OAS) calculated?

The application does **not** calculate the credit spread from raw bond prices. It retrieves the **pre-computed BBB US Corporate Option-Adjusted Spread (OAS)** published by ICE BofA, available through the FRED API.

**Two-tier retrieval** (`engine/market_data.py`, lines 141–180):

### Tier 1 — FRED API (preferred)

If a `FRED_API_KEY` environment variable is set, the application queries the FRED REST API for series **`BAMLC0A4CBBB`** (ICE BofA BBB US Corporate Index Option-Adjusted Spread):

```python
params = {
    "series_id": FRED_SPREAD_SERIES,   # "BAMLC0A4CBBB"
    "api_key": api_key,
    "file_type": "json",
    "sort_order": "desc",
    "limit": 5,
}
resp = requests.get(FRED_API_BASE, params=params, timeout=10)
```

It takes the most recent non-missing observation (skipping entries where `value == "."`), returning the spread in percentage points (e.g., `1.35` means 135 basis points).

### Tier 2 — VIX-based heuristic fallback

If no FRED API key is available (or the FRED call fails), the application falls back to a **linear heuristic estimate** derived from the VIX:

```python
estimated = 0.5 + vix * 0.09
```

This rough mapping produces:
| VIX | Estimated Spread |
|-----|-----------------|
| 12  | ~1.58%          |
| 20  | ~2.30%          |
| 30  | ~3.20%          |
| 50  | ~5.00%          |

**How the spread is used**: The regime engine uses two thresholds (`engine/config.py`, lines 36–37):
- **Elevated**: BBB OAS ≥ 2.50 percentage points — qualifies as stress confirmation for Regime B.
- **Extreme**: BBB OAS ≥ 4.50 percentage points — qualifies as extreme stress for Regime C.

---

## 4. How is the Trough Price calculated?

The trough price is the **lowest closing price during the current drawdown episode**, computed inside `compute_drawdown()` in `engine/market_data.py` (lines 78–118):

```python
def compute_drawdown(df: pd.DataFrame) -> dict:
    close = df["close"]
    running_max = close.cummax()
    drawdown_series = (close - running_max) / running_max

    trough_idx = drawdown_series.idxmin()
    trough_val = float(close.loc[trough_idx])
    ...
```

Step by step:

1. **`running_max = close.cummax()`** — Computes the cumulative maximum (running ATH) at each date.
2. **`drawdown_series = (close - running_max) / running_max`** — Computes the percentage drawdown from the running ATH at each date. Values are ≤ 0; a value of −0.25 means the price is 25% below its ATH at that point.
3. **`trough_idx = drawdown_series.idxmin()`** — Finds the date where the drawdown was deepest (most negative) over the entire 5-year history.
4. **`trough_val = close.loc[trough_idx]`** — Reads the actual closing price on that date.

The trough price is passed to the **recovery module** (`engine/recovery.py`) to compute the price levels at which the portfolio should de-escalate:

- **C → B recovery price**: `trough_price × (1 + 0.50)` = trough + 50%
- **B → A recovery price**: `C_to_B_price × (1 + 0.25)` = an additional 25% above the C→B level

---

## 5. Where does the Credit Spread data get fetched?

The credit spread data is fetched from the **Federal Reserve Economic Data (FRED)** service, specifically the **FRED REST API** at:

```
https://api.stlouisfed.org/fred/series/observations
```

**Configuration** (`engine/config.py`, lines 155–156):

```python
FRED_SPREAD_SERIES = "BAMLC0A4CBBB"  # ICE BofA BBB US Corporate OAS
FRED_API_BASE      = "https://api.stlouisfed.org/fred/series/observations"
```

**Series details**:
- **Series ID**: `BAMLC0A4CBBB`
- **Full name**: ICE BofA BBB US Corporate Index Option-Adjusted Spread
- **Publisher**: ICE Data Indices (distributed by the Federal Reserve Bank of St. Louis)
- **Frequency**: Daily (business days)
- **Units**: Percentage points (e.g., 1.50 = 150 basis points)

**Fetch implementation** (`engine/market_data.py`, lines 141–180): The `fetch_credit_spread()` function sends an HTTP GET request to the FRED API with the series ID and API key. It reads the most recent 5 observations (sorted descending), returning the first non-missing value. The result is cached in-memory for 30 minutes.

**Authentication**: A free FRED API key is required (set via the `FRED_API_KEY` environment variable). If unavailable, the application falls back to a VIX-based heuristic (see Question 3).

---

## 6. How are the "Equal-Value-Index Regional Weights" calculated?

The regional weights in the code are **static constants**, not dynamically computed. They represent the target allocations of the equity sleeve as of July 2025, derived from the GPO's Equal-Value-Index methodology.

**Configuration** (`engine/config.py`, lines 7–17):

```python
# Equal-Value Regional Weights (% of equity sleeve)
# Derived from the report's target allocations as of July 2025
EQUITY_WEIGHTS = {
    "north_america":    0.4848,   # 48.48%
    "europe":           0.1615,   # 16.15%
    "emerging_markets": 0.0814,   #  8.14%
    "small_caps":       0.0777,   #  7.77%
    "japan":            0.0587,   #  5.87%
    "pacific_ex_jp":    0.0175,   #  1.75%
}
```

These weights sum to approximately 0.8816 (88.16%) because they express each region's share of the total portfolio (including the reserve sleeve). The allocator normalizes them before use (`engine/allocator.py`, lines 74–76):

```python
eq_sum = sum(EQUITY_WEIGHTS.values())
normed_eq = {k: v / eq_sum for k, v in EQUITY_WEIGHTS.items()}
```

After normalization (dividing by their sum), each region's weight becomes its share **within the equity sleeve only**. For example, North America's normalized equity-sleeve share is `0.4848 / 0.8816 ≈ 54.98%`.

**The Equal-Value-Index methodology** — In contrast to market-cap weighting (where the US dominates at ~60–65% of MSCI World), the Equal-Value approach:

1. Weights regions by their aggregate **economic value** (GDP, earnings, book value) rather than market capitalization.
2. This systematically **underweights expensive/overvalued** regions and **overweights cheaper/undervalued** ones relative to a market-cap index.
3. Includes a dedicated **small-cap** allocation to capture the size premium, which is typically absent or underrepresented in market-cap-weighted global indices.

The specific percentage values (48.48%, 16.15%, etc.) come from the GPO fund's published target allocations and are hard-coded in the configuration as a snapshot of that methodology's output.

---

## 7. How are the ETFs in "ETF Universe" determined? Why is "iShares Core MSCI EM IMI UCITS ETF" the proxy for "MSCI EM IMI"?

The ETFs are **manually curated** based on a set of practical selection criteria designed to provide cost-efficient, liquid exposure to each target index. They are defined as static configuration in `engine/config.py` (lines 56–120).

### Selection criteria

Each ETF in the universe was chosen based on:

1. **Index tracking**: The ETF must track the specific index that represents the target region or asset class (e.g., MSCI EM IMI for emerging markets).
2. **UCITS compliance**: All equity ETFs are UCITS-compliant, making them suitable for European investors (tax-efficient, regulatory-compliant).
3. **Low Total Expense Ratio (TER)**: Cost minimization is a core principle. The selected ETFs have TERs ranging from 0.05% to 0.35%.
4. **Listing on European exchanges**: All tickers are listed on German (`.DE`) or French (`.PA`) exchanges for practical tradability by European investors.
5. **Fund size and liquidity**: Preference is given to large, well-established funds (the "Core" or "Prime" product lines from major issuers like iShares, Xtrackers, Lyxor/Amundi).

### Why "iShares Core MSCI EM IMI UCITS ETF" for emerging markets

The specific mapping is:

```python
"emerging_markets": {
    "name": "iShares Core MSCI EM IMI UCITS ETF",
    "isin": "IE00BKM4GZ66",
    "ticker": "IS3N.DE",
    "ter": 0.0018,       # 0.18%
    "index": "MSCI EM IMI",
},
```

This ETF is the proxy for the MSCI Emerging Markets Investable Market Index (EM IMI) because:

- **Exact index match**: The ETF physically replicates the MSCI EM IMI index, which is the broadest emerging-markets benchmark (including large, mid, and small caps across ~24 emerging markets). This aligns with the GPO's goal of capturing the full investable EM universe.
- **"Core" product line**: iShares "Core" ETFs are designed for long-term buy-and-hold investors, with very low fees (0.18%) and optimized tracking.
- **Largest UCITS EM ETF**: With over €18 billion AUM, it is the largest UCITS-compliant emerging-markets ETF, ensuring tight spreads and high liquidity.
- **IMI (Investable Market Index) breadth**: Unlike the standard MSCI EM index (large + mid cap only), the IMI variant includes small caps, providing ~3,400+ holdings versus ~1,400. This broader exposure is consistent with the Equal-Value philosophy of capturing value across the entire market-cap spectrum.
- **European listing**: Available on Xetra (IS3N.DE), the most liquid European exchange.

### Complete ETF Universe

| Region | ETF | Index | TER |
|--------|-----|-------|-----|
| North America | iShares Core S&P 500 UCITS ETF | S&P 500 | 0.07% |
| Europe | Lyxor Core STOXX Europe 600 UCITS ETF | STOXX Europe 600 | 0.07% |
| Emerging Markets | iShares Core MSCI EM IMI UCITS ETF | MSCI EM IMI | 0.18% |
| Small Caps | iShares MSCI World Small Cap UCITS ETF | MSCI World Small Cap | 0.35% |
| Japan | Amundi Prime Japan UCITS ETF | MSCI Japan | 0.05% |
| Pacific ex-Japan | iShares MSCI Pacific ex-Japan UCITS ETF | MSCI Pacific ex-Japan | 0.20% |
| Inflation-Linked | iShares Euro Inflation Linked Govt Bond UCITS ETF | Bloomberg Euro Govt Inflation-Linked | 0.20% |
| Money Market | Xtrackers II EUR Overnight Rate Swap UCITS ETF | EUR Overnight Rate | 0.10% |
| Gold | Xtrackers IE Physical Gold ETC | Gold Spot | 0.15% |

The same logic applies to every entry: each ETF is the lowest-cost, most liquid, UCITS-compliant product that tracks the exact target index for its assigned region or asset class.
