# Methodology FAQ

## 1) How is the MSCI World proxy calculated?

The app does **not** calculate an MSCI World index value itself. It uses a market-traded proxy ticker configured as:

- `MSCI_WORLD_PROXY = "URTH"` (iShares MSCI World ETF in USD).

Price history is then pulled with `yfinance` and represented as daily close values (`close`). Drawdown metrics are computed from that close series against a running all-time high.

## 2) How is the VIX (Fear Index) calculated?

The app does **not** derive VIX from options data. It fetches the latest close for `^VIX` via `yfinance` over the last 5 days and takes the most recent non-null close.

## 3) How is the Credit Spread (BBB OAS) calculated?

Primary path:

- Fetch FRED series `BAMLC0A4CBBB` (ICE BofA BBB US Corporate OAS) and return the latest non-missing observation.

Fallback path (if no FRED key or fetch failure):

- Estimate spread from VIX using:
- `estimated_spread = 0.5 + 0.09 * VIX`

## 4) How is the Trough Price calculated?

From the selected proxy price series (`close`):

1. Compute running max (`cummax`).
2. Compute drawdown series: `(close - running_max) / running_max`.
3. Find the index/date of minimum drawdown (`idxmin`).
4. Trough price is `close` at that date.

## 5) Where does the Credit Spread data get fetched?

It is fetched from the **FRED API endpoint**:

- `https://api.stlouisfed.org/fred/series/observations`
- with series id `BAMLC0A4CBBB`.

## 6) How are the “Equal-Value-Index Regional Weights” calculated?

In this implementation, the regional weights are configured as static constants (`EQUITY_WEIGHTS`) “derived from the report’s target allocations as of July 2025”.

At runtime, allocation code normalizes those configured regional weights to sum to 1.0 and then scales them by the current regime equity percentage (80%, 90%, or 100%).

## 7) How are the ETFs in “ETF Universe” determined?

In this codebase, the ETF universe is a static, curated mapping (`ETFS`) with one selected UCITS instrument per sleeve/region and a declared tracked index.

Example:

- `emerging_markets` maps to `iShares Core MSCI EM IMI UCITS ETF` with index label `MSCI EM IMI`.

There is **no separate scoring/selection algorithm** in the repository that dynamically chooses that ETF. The rationale in code is that it is the explicit configured proxy for that regional sleeve.
