"""
Recovery protocol calculator.

Computes the price levels at which the portfolio should transition
back from escalation regimes to normal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.config import RECOVERY_B_TO_A_RALLY, RECOVERY_C_TO_B_RALLY


@dataclass
class RecoveryLevels:
    current_regime: str
    trough_price: Optional[float]
    regime_c_to_b_price: Optional[float]   # +50 % from trough
    regime_b_to_a_price: Optional[float]   # additional +25 %
    current_price: Optional[float]
    progress_to_b: Optional[float]         # 0-100 %
    progress_to_a: Optional[float]         # 0-100 %


def compute_recovery_levels(
    current_regime: str,
    trough_price: Optional[float],
    current_price: Optional[float],
    ath_price: Optional[float] = None,
) -> RecoveryLevels:
    """
    Given the current regime and trough, compute the price targets
    for each recovery phase.
    """
    if trough_price is None or trough_price <= 0:
        return RecoveryLevels(
            current_regime=current_regime,
            trough_price=trough_price,
            regime_c_to_b_price=None,
            regime_b_to_a_price=None,
            current_price=current_price,
            progress_to_b=None,
            progress_to_a=None,
        )

    c_to_b = trough_price * (1 + RECOVERY_C_TO_B_RALLY)
    b_to_a = c_to_b * (1 + RECOVERY_B_TO_A_RALLY)

    progress_b: Optional[float] = None
    progress_a: Optional[float] = None

    if current_price is not None and current_price > trough_price:
        total_needed_b = c_to_b - trough_price
        gained = current_price - trough_price
        progress_b = min(100.0, round((gained / total_needed_b) * 100, 1))

        total_needed_a = b_to_a - trough_price
        progress_a = min(100.0, round((gained / total_needed_a) * 100, 1))

    return RecoveryLevels(
        current_regime=current_regime,
        trough_price=round(trough_price, 2),
        regime_c_to_b_price=round(c_to_b, 2),
        regime_b_to_a_price=round(b_to_a, 2),
        current_price=round(current_price, 2) if current_price else None,
        progress_to_b=progress_b,
        progress_to_a=progress_a,
    )
