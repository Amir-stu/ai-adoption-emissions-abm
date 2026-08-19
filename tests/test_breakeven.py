"""
The break-even solver and the rebound extension.

The thesis reads its result off the break-even values, so the closed-form
solutions have to agree with the simulation they claim to describe. Every test
here runs at a reduced replication count; the printed tables use N = 200.
"""
import pytest

import breakeven
import experiment
import model

BASELINE = "Baseline (no policy)"
N_FIRMS = 120
N_MC = 12
ZETA = 0.20


@pytest.fixture(scope="module")
def components():
    return {c: breakeven.run_components(c, BASELINE, n_firms=N_FIRMS, n_mc=N_MC)
            for c in ("EU", "Poland")}


# ---------------------------------------------------------------------------
# The closed-form solutions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("country", ["EU", "Poland"])
def test_solved_gamma_star_sets_the_decomposed_net_effect_to_zero(components, country):
    comp = components[country]
    solved = breakeven.gamma_star(comp, ZETA)
    assert breakeven.net_at(comp, gamma=solved, g=0.0, zeta=ZETA) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("country", ["EU", "Poland"])
def test_solved_g_star_sets_the_decomposed_net_effect_to_zero(components, country):
    comp = components[country]
    solved = breakeven.g_star(comp, ZETA)
    assert breakeven.net_at(comp, g=solved, zeta=ZETA) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("country", ["EU", "Poland"])
def test_solved_zeta_star_sets_the_decomposed_net_effect_to_zero(components, country):
    comp = components[country]
    solved = breakeven.zeta_star(comp)
    assert breakeven.net_at(comp, zeta=solved) == pytest.approx(0.0, abs=1e-9)


def test_the_unmodified_model_returns_zero_at_the_solved_gamma(components):
    """The claim the repository makes: the closed form is not merely internally
    consistent, it is what the agent loop produces when re-run at that value."""
    solved = breakeven.gamma_star(components["EU"], ZETA)
    realised = breakeven.verify_gamma("EU", BASELINE, solved, ZETA,
                                      n_firms=N_FIRMS, n_mc=N_MC)
    assert realised == pytest.approx(0.0, abs=1e-4)


def test_the_net_effect_falls_as_output_expansion_rises(components):
    comp = components["EU"]
    path = [breakeven.net_at(comp, g=g, zeta=ZETA) for g in (0.0, 0.01, 0.02, 0.04)]
    assert all(later < earlier for earlier, later in zip(path, path[1:]))


def test_the_analytic_ceiling_on_g_matches_the_thesis():
    """g_dagger = gamma / (1 - gamma*A) = 2.34% for a full adopter, Eq. (4.4)."""
    a_full = model.Firm.A_OF_STATE[model.Firm.STATE_F]
    g_dagger = model.GAMMA / (1.0 - model.GAMMA * a_full)
    assert g_dagger == pytest.approx(0.0234, abs=5e-5)


# ---------------------------------------------------------------------------
# The rebound extension
# ---------------------------------------------------------------------------

def test_zero_rebound_reproduces_the_base_model_exactly():
    """zeta = 0 must leave the model of model.py untouched, agent for agent."""
    with_rebound = experiment.run_cell("EU", BASELINE, 0.0, n_firms=N_FIRMS, n_mc=N_MC)
    base = model.run_scenario("EU", BASELINE, n_firms=N_FIRMS, n_mc=N_MC)
    assert with_rebound["net_mean"] == pytest.approx(base["net_mean"], abs=1e-12)


def test_the_net_effect_is_non_increasing_in_the_rebound_coefficient():
    """Common random numbers make this hold by construction, not up to noise."""
    nets = [experiment.run_cell("EU", BASELINE, z, n_firms=N_FIRMS, n_mc=N_MC)["net_mean"][-1]
            for z in experiment.ZETA_VALUES]
    assert all(later <= earlier for earlier, later in zip(nets, nets[1:]))


def test_the_sector_ranking_of_table_6_1_holds():
    """Transport carries a clear net benefit; ICT, the fastest adopter, does not.
    That contrast is the substantive result of Table 6.1."""
    cell = experiment.run_cell("EU", BASELINE, ZETA, n_firms=N_FIRMS, n_mc=N_MC)
    transport = cell["sector_net_mean"]["Transport & Storage"][-1]
    ict = cell["sector_net_mean"]["ICT"][-1]
    assert transport > 10.0
    assert ict < 1.0
    assert transport > ict
