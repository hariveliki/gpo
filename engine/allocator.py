"""
Portfolio allocation calculator.

Translates the regime state and portfolio value into concrete
position sizes and rebalancing trades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from engine.config import (
    EQUITY_WEIGHTS,
    ETFS,
    RESERVE_WEIGHTS,
    SIMPLE_ETFS,
)
from engine.regime import RegimeResult


@dataclass
class Position:
    region: str
    etf_name: str
    isin: str
    index: str
    ter: float
    target_weight: float       # weight of total portfolio (0-1)
    target_value: float        # in portfolio currency
    current_value: float = 0.0
    trade_value: float = 0.0   # positive = buy, negative = sell


@dataclass
class AllocationResult:
    portfolio_value: float
    regime: str
    equity_pct: float
    reserve_pct: float
    equity_value: float
    reserve_value: float
    positions: list[Position] = field(default_factory=list)
    simple_positions: list[Position] = field(default_factory=list)
    weighted_ter: float = 0.0
    rebalance_actions: list[str] = field(default_factory=list)


def compute_allocation(
    portfolio_value: float,
    regime: RegimeResult,
    current_holdings: Optional[dict[str, float]] = None,
) -> AllocationResult:
    """
    Compute the target allocation for the full 6-ETF model and
    the simplified 3-ETF model.

    Parameters
    ----------
    portfolio_value : float
        Total portfolio value in EUR.
    regime : RegimeResult
        Current regime state.
    current_holdings : dict | None
        Mapping of region key → current value. Used to compute
        rebalancing trades.
    """
    if current_holdings is None:
        current_holdings = {}

    equity_value = portfolio_value * regime.equity_pct
    reserve_value = portfolio_value * regime.reserve_pct

    # Normalize equity weights to sum to 1.0
    eq_sum = sum(EQUITY_WEIGHTS.values())
    normed_eq = {k: v / eq_sum for k, v in EQUITY_WEIGHTS.items()}

    positions: list[Position] = []
    total_ter_weight = 0.0

    for region, weight in normed_eq.items():
        etf = ETFS[region]
        abs_weight = weight * regime.equity_pct
        target_val = portfolio_value * abs_weight
        current_val = current_holdings.get(region, 0.0)
        trade = target_val - current_val

        positions.append(Position(
            region=region,
            etf_name=etf["name"],
            isin=etf["isin"],
            index=etf["index"],
            ter=etf["ter"],
            target_weight=abs_weight,
            target_value=target_val,
            current_value=current_val,
            trade_value=trade,
        ))
        total_ter_weight += abs_weight * etf["ter"]

    # Reserve positions
    for component, weight in RESERVE_WEIGHTS.items():
        if component == "cash":
            positions.append(Position(
                region="cash",
                etf_name="Cash / High-Yield Savings",
                isin="N/A",
                index="N/A",
                ter=0.0,
                target_weight=weight * regime.reserve_pct,
                target_value=portfolio_value * weight * regime.reserve_pct,
                current_value=current_holdings.get("cash", 0.0),
                trade_value=(portfolio_value * weight * regime.reserve_pct
                             - current_holdings.get("cash", 0.0)),
            ))
            continue

        etf = ETFS.get(component)
        if etf is None:
            continue
        abs_weight = weight * regime.reserve_pct
        target_val = portfolio_value * abs_weight
        current_val = current_holdings.get(component, 0.0)

        positions.append(Position(
            region=component,
            etf_name=etf["name"],
            isin=etf["isin"],
            index=etf["index"],
            ter=etf["ter"],
            target_weight=abs_weight,
            target_value=target_val,
            current_value=current_val,
            trade_value=target_val - current_val,
        ))
        total_ter_weight += abs_weight * etf["ter"]

    # Simplified 3-ETF model
    simple_positions: list[Position] = []
    for key, info in SIMPLE_ETFS.items():
        # Scale equity portion to regime
        if key == "cash":
            w = regime.reserve_pct
        elif key == "small_caps":
            w = 0.10 * (regime.equity_pct / 0.80)
        else:
            w = info["weight"] * (regime.equity_pct / 0.80)
            if key == "acwi_imi" and regime.reserve_pct < 0.20:
                w = regime.equity_pct - 0.10 * (regime.equity_pct / 0.80)

        simple_positions.append(Position(
            region=key,
            etf_name=info["name"],
            isin=info["isin"],
            index="",
            ter=info["ter"],
            target_weight=w,
            target_value=portfolio_value * w,
        ))

    # Rebalance action descriptions
    actions: list[str] = []
    for p in positions:
        if abs(p.trade_value) > 0.01 * portfolio_value:
            direction = "BUY" if p.trade_value > 0 else "SELL"
            actions.append(
                f"{direction} €{abs(p.trade_value):,.0f} of {p.etf_name} ({p.region})"
            )

    return AllocationResult(
        portfolio_value=portfolio_value,
        regime=regime.regime,
        equity_pct=regime.equity_pct,
        reserve_pct=regime.reserve_pct,
        equity_value=equity_value,
        reserve_value=reserve_value,
        positions=positions,
        simple_positions=simple_positions,
        weighted_ter=round(total_ter_weight * 100, 4),
        rebalance_actions=actions,
    )
