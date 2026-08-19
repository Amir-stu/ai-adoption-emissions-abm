"""
Table 4.1 -- Critical grid carbon intensity G* by sector
=======================================================

Bachelor thesis support script (Amir Ben Khadher, University of Mannheim).

Chapter 4 of the thesis is analytic, not simulated: for a single fully adopting
medium or large firm, the benefit and cost channels of Identity (4.1) are both
closed forms, so the grid intensity at which they cancel has a closed form too.
This script evaluates it; no agent loop is involved and no random draw is made.

    benefit(g) = E_base * [1 - (1 - gamma*A)(1 + g*A)]      tCO2e/yr
    cost(G)    = kWh_AI * G / 1000                          tCO2e/yr
    G*(g)      = 1000 * benefit(g) / kWh_AI                 kgCO2e/kWh

The inputs are the *published* values of the thesis, not the full-precision
Eurostat series carried inside model.py:

  * E_base is the EU total column of Table 5.1 (Scope 1 + Scope 2).
  * Firm electricity is the rounded GWh/yr figure printed in Table 5.2
    (ICT 0.88, Manufacturing and Electronics 2.50, Transport 0.92,
    Finance 0.99, Accommodation & Food 0.35), and AI electricity is 2.75% of
    it -- the midpoint of the full-adopter draw U(1.5%, 4.0%).

Using the printed values rather than the unrounded series is deliberate: it
makes every number in Table 4.1 recomputable from the thesis alone. The
difference against the unrounded series is below the two significant figures
the table reports.

Output: results/table4_1_threshold.csv
"""
import pandas as pd

from paths import results

GAMMA = 0.023          # transferred carbon-intensity benchmark, Zhou & Bu (2026)
A_FULL = 0.75          # adoption intensity of a full adopter
AI_SHARE_MID = 0.0275  # midpoint of the full-adopter draw U(1.5%, 4.0%)
G_GRID_EU = 0.2112     # EU grid intensity, kgCO2e/kWh (Ember, 2024)
G_VALUES = (0.00, 0.01, 0.02)

# sector -> (E_base EU total tCO2e/yr [Table 5.1], firm electricity GWh/yr [Table 5.2])
SECTORS = {
    "Transport & Storage":  (4164, 0.92),
    "Manufacturing":        (2594, 2.50),
    "Finance":              (556, 0.99),
    "Electronics & Pharma": (928, 2.50),
    "Accommodation & Food": (135, 0.35),
    "ICT":                  (268, 0.88),
}

# National grid intensities in the base year, for the table footnote.
GRID_FACTORS_0 = {
    "France": 0.04048, "EU": 0.2112, "US": 0.38378, "China": 0.5554, "Poland": 0.60818,
}


def benefit(e_base, g, gamma=GAMMA, a=A_FULL):
    """Emissions avoided per year, in tCO2e, at output expansion g."""
    return e_base * (1.0 - (1.0 - gamma * a) * (1.0 + g * a))


def g_star_intensity(e_base, kwh_ai, g):
    """Grid intensity, kgCO2e/kWh, at which benefit(g) equals AI energy cost."""
    return 1000.0 * benefit(e_base, g) / kwh_ai


def net_on_grid(e_base, kwh_ai, grid, g=0.0):
    """Net effect in tCO2e/yr on a grid of the given carbon intensity."""
    return benefit(e_base, g) - kwh_ai * grid / 1000.0


def build_table():
    rows = []
    for sector, (e_base, gwh) in SECTORS.items():
        kwh_ai = gwh * 1e6 * AI_SHARE_MID
        row = {
            "sector": sector,
            "E_base_tCO2e_per_yr": e_base,
            "AI_kWh_per_yr": round(kwh_ai),
        }
        for g in G_VALUES:
            row["G_star_g%d" % round(g * 100)] = round(g_star_intensity(e_base, kwh_ai, g), 2)
        row["net_EU_grid_tCO2e_per_yr"] = round(net_on_grid(e_base, kwh_ai, G_GRID_EU), 1)
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_table()

    print("=== Table 4.1: critical grid intensity G* (kgCO2e/kWh) ===")
    print("gamma = %.3f, A = %.2f, AI electricity = %.2f%% of firm electricity\n"
          % (GAMMA, A_FULL, 100 * AI_SHARE_MID))
    print(df.to_string(index=False))
    print("\nGrid intensities (kgCO2e/kWh, 2024): "
          + ", ".join("%s %.3f" % (c, v) for c, v in GRID_FACTORS_0.items()))

    out = results("table4_1_threshold.csv")
    df.to_csv(out, index=False)
    print("\nSaved: results/%s" % out.name)
