"""
Regime detection engine implementing the GPO's three-state model.

Regime A  – Normal          (80 / 20)
Regime B  – Equity Scarcity (90 / 10)
Regime C  – Escalation      (100 / 0)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.config import (
    REGIME_A_EQUITY,
    REGIME_A_RESERVE,
    REGIME_B_DRAWDOWN_TRIGGER,
    REGIME_B_EQUITY,
    REGIME_B_RESERVE,
    REGIME_C_DRAWDOWN_TRIGGER,
    REGIME_C_EQUITY,
    REGIME_C_RESERVE,
    SPREAD_ELEVATED,
    SPREAD_EXTREME,
)


@dataclass
class RegimeResult:
    regime: str            # "A", "B", or "C"
    label: str             # Human-readable label
    equity_pct: float      # Target equity allocation (0-1)
    reserve_pct: float     # Target reserve allocation (0-1)
    drawdown_pct: float    # Current drawdown (negative %)
    spread: Optional[float]
    vix: Optional[float]
    triggers_met: list[str]
    description: str


def detect_regime(
    drawdown_pct: float,
    credit_spread: Optional[float] = None,
    vix: Optional[float] = None,
) -> RegimeResult:
    """
    Determine the current market regime based on drawdown depth and
    credit-spread / VIX stress indicators.

    Parameters
    ----------
    drawdown_pct : float
        Current drawdown from ATH expressed as a negative percentage
        (e.g. -25.0 means 25 % below ATH).
    credit_spread : float | None
        BBB OAS in percentage points.
    vix : float | None
        VIX index level.

    Returns
    -------
    RegimeResult
    """
    drawdown_decimal = drawdown_pct / 100.0 if abs(drawdown_pct) > 1 else drawdown_pct
    triggers: list[str] = []

    # --- Credit stress flags ------------------------------------------------
    spread_elevated = False
    spread_extreme = False
    if credit_spread is not None:
        if credit_spread >= SPREAD_EXTREME:
            spread_extreme = True
            spread_elevated = True
            triggers.append(f"Credit spread {credit_spread:.2f}% ≥ {SPREAD_EXTREME}% (extreme)")
        elif credit_spread >= SPREAD_ELEVATED:
            spread_elevated = True
            triggers.append(f"Credit spread {credit_spread:.2f}% ≥ {SPREAD_ELEVATED}% (elevated)")

    vix_stressed = False
    if vix is not None and vix >= 30:
        vix_stressed = True
        triggers.append(f"VIX {vix:.1f} ≥ 30")

    stress_confirmed = spread_elevated or vix_stressed

    # --- Regime C check -----------------------------------------------------
    if drawdown_decimal <= REGIME_C_DRAWDOWN_TRIGGER and (spread_extreme or stress_confirmed):
        triggers.insert(0, f"Drawdown {drawdown_pct:.1f}% ≤ {REGIME_C_DRAWDOWN_TRIGGER*100:.0f}%")
        return RegimeResult(
            regime="C",
            label="Escalation",
            equity_pct=REGIME_C_EQUITY,
            reserve_pct=REGIME_C_RESERVE,
            drawdown_pct=drawdown_pct,
            spread=credit_spread,
            vix=vix,
            triggers_met=triggers,
            description=(
                "Full-scale market panic detected. Deploy ALL remaining reserves "
                "into equities. Target allocation: 100% Equity / 0% Reserve."
            ),
        )

    # --- Regime B check -----------------------------------------------------
    if drawdown_decimal <= REGIME_B_DRAWDOWN_TRIGGER and stress_confirmed:
        triggers.insert(0, f"Drawdown {drawdown_pct:.1f}% ≤ {REGIME_B_DRAWDOWN_TRIGGER*100:.0f}%")
        return RegimeResult(
            regime="B",
            label="Equity Scarcity",
            equity_pct=REGIME_B_EQUITY,
            reserve_pct=REGIME_B_RESERVE,
            drawdown_pct=drawdown_pct,
            spread=credit_spread,
            vix=vix,
            triggers_met=triggers,
            description=(
                "Equity scarcity detected. Deploy 50% of the Investment Reserve "
                "into equities. Target allocation: 90% Equity / 10% Reserve."
            ),
        )

    # --- Regime A (default) -------------------------------------------------
    return RegimeResult(
        regime="A",
        label="Normal",
        equity_pct=REGIME_A_EQUITY,
        reserve_pct=REGIME_A_RESERVE,
        drawdown_pct=drawdown_pct,
        spread=credit_spread,
        vix=vix,
        triggers_met=triggers if triggers else ["No crisis triggers active"],
        description=(
            "Markets operating normally. Maintain standard allocation: "
            "80% Equity / 20% Reserve. Rebalance quarterly."
        ),
    )
