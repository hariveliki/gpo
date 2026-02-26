"""
Tests for the Global Portfolio One replication engine.
"""

import pytest

from engine.allocator import compute_allocation
from engine.recovery import compute_recovery_levels
from engine.regime import RegimeResult, detect_regime


# --------------------------------------------------------------------------- #
# Regime Detection
# --------------------------------------------------------------------------- #

class TestRegimeDetection:
    def test_regime_a_normal_market(self):
        r = detect_regime(-5.0, credit_spread=1.5, vix=15)
        assert r.regime == "A"
        assert r.equity_pct == 0.80
        assert r.reserve_pct == 0.20

    def test_regime_b_with_spread_stress(self):
        r = detect_regime(-25.0, credit_spread=3.0, vix=20)
        assert r.regime == "B"
        assert r.equity_pct == 0.90
        assert r.reserve_pct == 0.10

    def test_regime_b_with_vix_stress(self):
        r = detect_regime(-22.0, credit_spread=1.0, vix=35)
        assert r.regime == "B"

    def test_regime_c_full_panic(self):
        r = detect_regime(-45.0, credit_spread=5.0, vix=50)
        assert r.regime == "C"
        assert r.equity_pct == 1.0
        assert r.reserve_pct == 0.0

    def test_drawdown_alone_insufficient_for_regime_b(self):
        r = detect_regime(-25.0, credit_spread=1.0, vix=12)
        assert r.regime == "A"

    def test_stress_alone_insufficient_for_regime_b(self):
        r = detect_regime(-10.0, credit_spread=4.0, vix=35)
        assert r.regime == "A"

    def test_regime_c_needs_extreme_stress(self):
        r = detect_regime(-45.0, credit_spread=2.0, vix=25)
        assert r.regime == "A"

    def test_regime_c_with_vix_stress(self):
        r = detect_regime(-42.0, credit_spread=1.0, vix=40)
        assert r.regime == "C"

    def test_no_data(self):
        r = detect_regime(0.0, credit_spread=None, vix=None)
        assert r.regime == "A"

    def test_triggers_populated(self):
        r = detect_regime(-30.0, credit_spread=3.5, vix=35)
        assert r.regime == "B"
        assert len(r.triggers_met) >= 2


# --------------------------------------------------------------------------- #
# Allocation
# --------------------------------------------------------------------------- #

class TestAllocation:
    def test_regime_a_allocation_sums_to_100(self):
        regime = detect_regime(-5.0, credit_spread=1.0, vix=15)
        result = compute_allocation(100000, regime)
        total = sum(p.target_value for p in result.positions)
        assert abs(total - 100000) < 1.0

    def test_regime_b_equity_increases(self):
        regime_a = detect_regime(-5.0, credit_spread=1.0, vix=15)
        regime_b = detect_regime(-25.0, credit_spread=3.0, vix=35)

        alloc_a = compute_allocation(100000, regime_a)
        alloc_b = compute_allocation(100000, regime_b)

        assert alloc_b.equity_value > alloc_a.equity_value
        assert alloc_b.reserve_value < alloc_a.reserve_value

    def test_regime_c_full_equity(self):
        regime = detect_regime(-45.0, credit_spread=5.5, vix=60)
        result = compute_allocation(100000, regime)
        assert result.equity_value == 100000
        assert result.reserve_value == 0

    def test_small_portfolio(self):
        regime = detect_regime(-5.0, credit_spread=1.0, vix=15)
        result = compute_allocation(5000, regime)
        total = sum(p.target_value for p in result.positions)
        assert abs(total - 5000) < 1.0

    def test_simple_positions_present(self):
        regime = detect_regime(-5.0, credit_spread=1.0, vix=15)
        result = compute_allocation(100000, regime)
        assert len(result.simple_positions) == 3

    def test_weighted_ter_reasonable(self):
        regime = detect_regime(-5.0, credit_spread=1.0, vix=15)
        result = compute_allocation(100000, regime)
        assert 0 < result.weighted_ter < 0.5

    def test_custom_equity_weights(self):
        regime = detect_regime(-5.0, credit_spread=1.0, vix=15)
        custom_eq = {"north_america": 0.50, "europe": 0.50}
        result = compute_allocation(100000, regime, equity_weights=custom_eq)
        eq_positions = [p for p in result.positions if p.region in custom_eq]
        assert len(eq_positions) == 2
        assert abs(eq_positions[0].target_value - eq_positions[1].target_value) < 1.0

    def test_custom_reserve_weights(self):
        regime = detect_regime(-5.0, credit_spread=1.0, vix=15)
        custom_res = {"inflation_linked": 1.0, "money_market": 0.0, "gold": 0.0, "cash": 0.0}
        result = compute_allocation(100000, regime, reserve_weights=custom_res)
        res_positions = [p for p in result.positions if p.region == "inflation_linked"]
        assert len(res_positions) == 1
        assert res_positions[0].target_value == pytest.approx(20000, abs=1.0)

    def test_custom_weights_allocation_sums_correctly(self):
        regime = detect_regime(-5.0, credit_spread=1.0, vix=15)
        custom_eq = {"north_america": 0.30, "europe": 0.30, "emerging_markets": 0.20, "small_caps": 0.10, "japan": 0.05, "pacific_ex_jp": 0.05}
        result = compute_allocation(100000, regime, equity_weights=custom_eq)
        total = sum(p.target_value for p in result.positions)
        assert abs(total - 100000) < 1.0


# --------------------------------------------------------------------------- #
# Recovery Protocol
# --------------------------------------------------------------------------- #

class TestRecovery:
    def test_c_to_b_target(self):
        rec = compute_recovery_levels("C", trough_price=60.0, current_price=75.0)
        assert rec.regime_c_to_b_price == 90.0  # 60 * 1.5

    def test_b_to_a_target(self):
        rec = compute_recovery_levels("C", trough_price=60.0, current_price=75.0)
        assert rec.regime_b_to_a_price == 112.5  # 90 * 1.25

    def test_progress_calculation(self):
        rec = compute_recovery_levels("C", trough_price=60.0, current_price=90.0)
        assert rec.progress_to_b == 100.0

    def test_no_trough(self):
        rec = compute_recovery_levels("A", trough_price=None, current_price=100.0)
        assert rec.regime_c_to_b_price is None

    def test_zero_trough(self):
        rec = compute_recovery_levels("A", trough_price=0, current_price=100.0)
        assert rec.regime_c_to_b_price is None


# --------------------------------------------------------------------------- #
# Flask API
# --------------------------------------------------------------------------- #

class TestFlaskAPI:
    @pytest.fixture
    def client(self):
        from app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_homepage(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Global Portfolio One" in resp.data

    def test_reference_api(self, client):
        resp = client.get("/api/reference")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "equity_weights" in data
        assert "etfs" in data

    def test_simulate_api_regime_a(self, client):
        resp = client.post("/api/simulate", json={
            "drawdown_pct": -5,
            "credit_spread": 1.0,
            "vix": 15,
            "portfolio_value": 50000,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["regime"]["regime"] == "A"

    def test_simulate_api_regime_b(self, client):
        resp = client.post("/api/simulate", json={
            "drawdown_pct": -30,
            "credit_spread": 3.5,
            "vix": 40,
            "portfolio_value": 100000,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["regime"]["regime"] == "B"
        assert data["allocation"]["equity_pct"] == 0.9

    def test_simulate_api_regime_c(self, client):
        resp = client.post("/api/simulate", json={
            "drawdown_pct": -50,
            "credit_spread": 6.0,
            "vix": 70,
            "portfolio_value": 100000,
        })
        data = resp.get_json()
        assert data["regime"]["regime"] == "C"
        assert data["allocation"]["equity_value"] == 100000

    def test_dashboard_api(self, client):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "market" in data
        assert "regime" in data

    def test_allocate_api(self, client):
        resp = client.post("/api/allocate", json={"portfolio_value": 100000})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "allocation" in data
        assert data["allocation"]["portfolio_value"] == 100000

    def test_simulate_with_custom_weights(self, client):
        custom_eq = {"north_america": 0.50, "europe": 0.50}
        resp = client.post("/api/simulate", json={
            "drawdown_pct": -5,
            "credit_spread": 1.0,
            "vix": 15,
            "portfolio_value": 100000,
            "equity_weights": custom_eq,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        positions = data["allocation"]["positions"]
        eq_positions = [p for p in positions if p["region"] in custom_eq]
        assert len(eq_positions) == 2
        assert abs(eq_positions[0]["target_weight"] - eq_positions[1]["target_weight"]) < 0.001

    def test_allocate_with_custom_reserve_weights(self, client):
        custom_res = {"inflation_linked": 0.80, "money_market": 0.10, "gold": 0.05, "cash": 0.05}
        resp = client.post("/api/allocate", json={
            "portfolio_value": 100000,
            "reserve_weights": custom_res,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "allocation" in data
