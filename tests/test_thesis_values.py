"""
Cross-checks against the printed thesis.

Every value asserted here appears in the text of the thesis. If a parameter in
the code is edited without the thesis being edited too, these tests fail, which
is the point: the repository claims to reproduce the printed numbers, and this
is where that claim is enforced.
"""
import pytest

import model
import threshold

EU_GRID = 0.2112     # kgCO2e/kWh, Ember 2024 via Our World in Data, Table 5.2


# ---------------------------------------------------------------------------
# Table 5.1 -- baseline emissions per firm, EU column (tCO2e/yr)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sector, printed", [
    ("ICT", 268),
    ("Electronics & Pharma", 928),
    ("Manufacturing", 2594),
    ("Transport & Storage", 4164),
    ("Finance", 556),
    ("Accommodation & Food", 135),
])
def test_baseline_emissions_match_table_5_1(sector, printed):
    spec = model.SECTORS[sector]
    e_base = spec["scope1"] + spec["elec_kwh"] * model.GRID_FACTORS_0["EU"] / 1000.0
    assert e_base == pytest.approx(printed, abs=1.0)


# ---------------------------------------------------------------------------
# Table 5.2 -- parameters
# ---------------------------------------------------------------------------

def test_the_transferred_intensity_benchmark_is_2_3_percent():
    assert model.GAMMA == 0.023


def test_adoption_intensities_are_three_and_six_of_eight_business_functions():
    assert model.Firm.A_OF_STATE == (0.00, 0.375, 0.75)


def test_firm_size_shares_match_the_eibis_distribution():
    shares = model.Firm.SIZE_SHARES
    n = len(shares)
    assert shares.count("small") / n == pytest.approx(0.45, abs=0.01)
    assert shares.count("medium") / n == pytest.approx(0.36, abs=0.01)
    assert shares.count("large") / n == pytest.approx(0.18, abs=0.01)


def test_grid_intensities_match_the_ember_series():
    assert model.GRID_FACTORS_0 == pytest.approx({
        "France": 0.04048, "EU": 0.21120, "US": 0.38378,
        "China": 0.55540, "Poland": 0.60818,
    })


def test_the_ai_electricity_shares_bracket_the_iea_benchmark():
    assert model.AI_SHARE_PARTIAL == (0.005, 0.015)
    assert model.AI_SHARE_FULL == (0.015, 0.040)


def test_the_baseline_holds_output_fixed():
    """g is a scenario, swept in breakeven.py; the model itself runs at g = 0."""
    assert model.OUTPUT_EXPANSION == 0.0


# ---------------------------------------------------------------------------
# Table 4.1 -- critical grid intensity G* (kgCO2e/kWh)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sector, printed", [
    ("Manufacturing", 0.65),
    ("ICT", 0.19),
    ("Transport & Storage", 2.84),
])
def test_critical_grid_intensity_matches_table_4_1(sector, printed):
    table = threshold.build_table().set_index("sector")
    assert table.loc[sector, "G_star_g0"] == pytest.approx(printed, abs=0.005)


def test_manufacturing_clears_the_eu_grid_and_ict_does_not():
    """Section 6.1: manufacturing's G* lies above the EU grid factor, ICT's below.
    That single comparison is the chapter's headline."""
    table = threshold.build_table().set_index("sector")
    assert table.loc["Manufacturing", "G_star_g0"] > EU_GRID
    assert table.loc["ICT", "G_star_g0"] < EU_GRID
