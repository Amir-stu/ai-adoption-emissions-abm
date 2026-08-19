"""
Tables 6.1 and 6.2 -- sector, rebound and country x policy results
==================================================================

Amir Ben Khadher, University of Mannheim. Support code for the bachelor thesis
"The Double-Edged Sword: AI Adoption, Labour Productivity, and Carbon Emissions".

Runs the factorial design of experiment.py (imported unmodified) at a uniform
N = 200 Monte Carlo replications of 200 agents per cell. The replication count is
uniform by design: raising N only for the cells that look noisy would itself bias
the reported pattern.

Outputs
    results/table6_1_sector.csv          Table 6.1, trajectory columns (EU grid,
                                            baseline policy, zeta = 0)
    results/table6_1_rebound.csv         Table 6.1, rebound sweep at 2040
    results/table6_2_country_policy.csv  Table 6.2, country x policy at zeta = 0.20
"""

import pandas as pd

import experiment
from model import SECTOR_NAMES, GRID_FACTORS_0, POLICY_SCENARIOS, T_START
from paths import results

N_MC = 200                                       # uniform across every table
COUNTRY_ORDER = sorted(GRID_FACTORS_0, key=GRID_FACTORS_0.get)
POLICY_ORDER = list(POLICY_SCENARIOS.keys())
BASELINE = "Baseline (no policy)"
ZETA_VALUES = experiment.ZETA_VALUES
ZETA_CENTRAL = 0.20                              # the central rebound coefficient


def cell(country, policy, zeta):
    return experiment.run_cell(country, policy, zeta, n_mc=N_MC)


if __name__ == "__main__":
    print(f"Running factorial design at N = {N_MC} replications ...")

    # --- Table 6.2: country x policy at the central rebound coefficient ----
    rows = []
    for country in COUNTRY_ORDER:
        for policy in POLICY_ORDER:
            res = cell(country, policy, ZETA_CENTRAL)
            rows.append({
                "country": country, "policy": policy,
                "net_2040": res["net_mean"][-1],
                "lo": res["net_lo"][-1], "hi": res["net_hi"][-1],
                "tau_star": experiment.tipping_year(res["net_mean"]),
            })
        print(f"  {country}: done.")
    cp = pd.DataFrame(rows)
    cp.to_csv(results("table6_2_country_policy.csv"), index=False)
    print(f"\n=== Table 6.2: net CO2 at 2040 by country and policy "
          f"(zeta = {ZETA_CENTRAL}) ===")
    print(cp.to_string(index=False, float_format=lambda v: f"{v:.1f}"))

    # --- Table 6.1: sector results on the EU grid -------------------------
    eu = {z: cell("EU", BASELINE, z) for z in ZETA_VALUES}

    sec_rows = []
    for s in SECTOR_NAMES:
        traj = eu[0.00]["sector_net_mean"][s]
        sec_rows.append({"sector": s, "net_2025": traj[0],
                         "net_2032": traj[2032 - T_START], "net_2040": traj[-1]})
    sec = pd.DataFrame(sec_rows)
    sec.to_csv(results("table6_1_sector.csv"), index=False)
    print("\n=== Table 6.1, trajectory: net CO2 by sector "
          "(EU grid, baseline, zeta = 0) ===")
    print(sec.to_string(index=False, float_format=lambda v: f"{v:.1f}"))

    reb_rows = []
    for s in SECTOR_NAMES:
        r = {"sector": s}
        for z in ZETA_VALUES:
            r[f"zeta_{z:.2f}"] = eu[z]["sector_net_mean"][s][-1]
        r["pct_change"] = 100 * (r["zeta_0.30"] / r["zeta_0.00"] - 1)
        reb_rows.append(r)
    reb = pd.DataFrame(reb_rows)
    reb.to_csv(results("table6_1_rebound.csv"), index=False)
    print("\n=== Table 6.1, rebound sweep: erosion by sector "
          "(EU grid, baseline) ===")
    print(reb.to_string(index=False, float_format=lambda v: f"{v:.1f}"))

    print("\nSaved: table6_2_country_policy.csv, table6_1_sector.csv, table6_1_rebound.csv")
