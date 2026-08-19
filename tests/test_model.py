"""
The mechanics of the agent and the population.

These tests check the properties the thesis relies on when it reads the output:
that the emissions identity is exact rather than a first-order approximation,
that adoption is a one-way three-state process, that a policy ceiling can only
clean a grid, and that a fixed seed reproduces a run exactly.
"""
import random

import pytest

import model
from model import (
    GAMMA, GRID_DECARB, GRID_FACTORS_0, SECTOR_NAMES,
    Firm, FirmPopulation, deterministic_seed, grid_intensity_at, run_scenario,
)

BASELINE = "Baseline (no policy)"


def make_firm(size="large", sector="Manufacturing", country="EU", seed=0):
    firm = Firm(0, sector, random.Random(seed), country)
    firm.size = size
    firm.gamma = firm._assign_gamma()
    return firm


# ---------------------------------------------------------------------------
# The emissions identity, Eq. (5.3) to (5.5)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state", [Firm.STATE_N, Firm.STATE_P, Firm.STATE_F])
@pytest.mark.parametrize("g", [0.0, 0.01, 0.02, 0.04])
def test_benefit_fraction_is_the_exact_identity_not_a_linearisation(state, g, monkeypatch):
    """1 - (1-gamma*A)(1+g*A), including the second-order interaction term."""
    monkeypatch.setattr(model, "OUTPUT_EXPANSION", g)
    firm = make_firm()
    firm.state = state
    a = Firm.A_OF_STATE[state]

    expected = 1.0 - (1.0 - GAMMA * a) * (1.0 + g * a)
    assert firm.benefit_fraction() == pytest.approx(expected, abs=1e-15)

    # the linearised form drops gamma*g*A^2, so the two must differ once both
    # channels are active
    linear = a * (GAMMA - g)
    if g > 0 and a > 0:
        assert firm.benefit_fraction() != pytest.approx(linear, abs=1e-12)


def test_small_firms_carry_neither_channel():
    """No productivity premium is estimated for small firms, so gamma is zero."""
    firm = make_firm(size="small")
    firm.state = Firm.STATE_F
    assert firm.gamma == 0.0
    assert firm.benefit_fraction() == 0.0


def test_non_adopters_have_no_benefit_and_no_energy_cost():
    firm = make_firm()
    assert firm.state == Firm.STATE_N
    assert firm.benefit_fraction() == 0.0
    assert firm.ai_energy_kwh(elec_mult=1.0) == 0.0
    assert firm.net_co2(grid_intensity=0.5, elec_mult=1.0) == 0.0


def test_net_co2_is_benefit_minus_energy_cost():
    firm = make_firm()
    firm.state = Firm.STATE_F
    grid = GRID_FACTORS_0["EU"]

    benefit = firm.e_base * firm.benefit_fraction()
    cost = firm.ai_energy_kwh(1.0) * grid / 1000.0
    assert firm.net_co2(grid, 1.0) == pytest.approx(benefit - cost, abs=1e-12)


def test_baseline_emissions_are_scope_1_plus_scope_2():
    """Eq. (5.6): country-scaled Scope 1 plus own electricity at the own grid."""
    firm = make_firm(sector="ICT", country="Poland")
    scope1 = model.SECTORS["ICT"]["scope1"] * model.CO2_INTENSITY_REL_EU["Poland"]
    scope2 = model.SECTORS["ICT"]["elec_kwh"] * GRID_FACTORS_0["Poland"] / 1000.0
    assert firm.e_base == pytest.approx(scope1 + scope2)


# ---------------------------------------------------------------------------
# The adoption process
# ---------------------------------------------------------------------------

def test_adoption_advances_one_state_at_a_time_and_never_regresses():
    firm = make_firm()
    always = random.Random(1)
    for expected in (Firm.STATE_P, Firm.STATE_F, Firm.STATE_F, Firm.STATE_F):
        firm.maybe_adopt(hazard=1.0, rng=always)
        assert firm.state == expected


def test_a_zero_hazard_never_moves_an_agent():
    firm = make_firm()
    for _ in range(100):
        firm.maybe_adopt(hazard=0.0, rng=random.Random(7))
    assert firm.state == Firm.STATE_N


def test_adoption_share_is_monotone_and_bounded():
    rng = random.Random(3)
    population = FirmPopulation(120, rng, "EU")
    previous = 0.0
    for _ in range(model.T_YEARS):
        population.step(phi_boost=0.0, rng=rng)
        share = population.adoption_share()
        assert previous <= share <= 1.0
        previous = share
    assert share > 0.5, "diffusion should be well advanced by 2040"


def test_sector_shares_are_computed_within_sectors():
    rng = random.Random(5)
    population = FirmPopulation(200, rng, "EU")
    for _ in range(5):
        population.step(phi_boost=0.0, rng=rng)
    shares = [population.sector_adoption_share(s) for s in SECTOR_NAMES]
    assert all(0.0 <= s <= 1.0 for s in shares)
    assert len(set(shares)) > 1, "sector-specific coefficients must separate sectors"


# ---------------------------------------------------------------------------
# The environment
# ---------------------------------------------------------------------------

def test_the_grid_decarbonises_monotonically():
    grid0 = GRID_FACTORS_0["US"]
    path = [grid_intensity_at(t, grid0, None, GRID_DECARB["US"]) for t in range(16)]
    assert path[0] == pytest.approx(grid0)
    assert all(later < earlier for earlier, later in zip(path, path[1:]))


def test_a_policy_ceiling_can_only_clean_a_grid():
    """France starts below the renewable-mandate floor; the mandate must not
    raise its grid factor."""
    mandate = model.POLICY_SCENARIOS["Renewable Energy Mandate"]["grid_override"]
    france = grid_intensity_at(0, GRID_FACTORS_0["France"], mandate, GRID_DECARB["France"])
    poland = grid_intensity_at(0, GRID_FACTORS_0["Poland"], mandate, GRID_DECARB["Poland"])
    assert france == pytest.approx(GRID_FACTORS_0["France"])
    assert poland == pytest.approx(mandate)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_seed_keys_are_stable_across_processes():
    """zlib.crc32, not the salted built-in hash(): the value is fixed forever."""
    assert deterministic_seed("EU", "Baseline (no policy)", 0, 42) == 1189705792
    assert deterministic_seed("EU", "Baseline (no policy)", 1, 42) == 4266991397


def test_a_scenario_reproduces_itself_exactly():
    first = run_scenario("EU", BASELINE, n_firms=60, n_mc=5)
    second = run_scenario("EU", BASELINE, n_firms=60, n_mc=5)
    assert (first["net_mean"] == second["net_mean"]).all()
    assert (first["adopt_mean"] == second["adopt_mean"]).all()


def test_different_seeds_give_different_runs():
    first = run_scenario("EU", BASELINE, n_firms=60, n_mc=5, base_seed=42)
    second = run_scenario("EU", BASELINE, n_firms=60, n_mc=5, base_seed=43)
    assert (first["net_mean"] != second["net_mean"]).any()
