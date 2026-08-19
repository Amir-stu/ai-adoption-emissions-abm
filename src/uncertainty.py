"""
Table 6.5 -- uncertainty decomposition
======================================

Amir Ben Khadher, University of Mannheim. Support code for the bachelor thesis
"The Double-Edged Sword: AI Adoption, Labour Productivity, and Carbon Emissions".

Simulation output of this kind carries two distinct spreads that are easy to
conflate, and this script separates them at 2040 under the baseline policy:

  (A) AGENT HETEROGENEITY -- the distribution across the 40,000 individual firms
      simulated in a cell (200 agents x 200 replications): how different are firms
      from one another?
  (B) MONTE CARLO ERROR   -- the distribution of the 200 replication means: how
      precisely has the simulation pinned down its own average?

They differ by roughly a factor of sqrt(200). Reporting (B) while describing (A)
would overstate what is known about individual firms and understate the dispersion
the agent loop generates. A third uncertainty, about the parameters themselves, is
captured by neither and is addressed by breakeven.py.

The report is written to stdout; run_all.py captures it as
results/table6_5_uncertainty.txt.
"""
import io
import random
import statistics
import sys

import numpy as np

from model import (
    GRID_DECARB, GRID_FACTORS_0, POLICY_SCENARIOS, SECTOR_NAMES, SEED, T_YEARS,
    FirmPopulation, deterministic_seed, grid_intensity_at,
)

# The report contains no non-ASCII characters, but the console encoding on Windows
# is not guaranteed; force UTF-8 so the captured file is identical on every host.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

N_FIRMS = 200
N_MC = 200
BASE = "Baseline (no policy)"
ZETA = 0.20                       # central rebound coefficient, as in Tables 6.2-6.4
COUNTRIES = ["France", "EU", "US", "China", "Poland"]


def run(country):
    """Return (replication means, per-firm net effects) at 2040 for one country.

    Each replication advances a fresh population to 2040 and then evaluates the
    net effect of every agent under the last year's grid factor, so the per-firm
    array holds N_MC * N_FIRMS individual outcomes.
    """
    policy = POLICY_SCENARIOS[BASE]
    grid0 = GRID_FACTORS_0[country]
    replication_means = []
    per_firm = []

    for replication in range(N_MC):
        rng = random.Random(deterministic_seed(country, BASE, replication, SEED))
        population = FirmPopulation(N_FIRMS, rng, country)
        for t_idx in range(T_YEARS):
            population.step(policy["phi_boost"], rng, policy.get("fastest", False))
            grid = grid_intensity_at(t_idx, grid0, policy["grid_override"],
                                     GRID_DECARB[country])

        shares = {s: population.sector_adoption_share(s) for s in SECTOR_NAMES}
        nets = []
        for firm in population.firms:
            benefit = firm.e_base * firm.benefit_fraction()
            cost = (firm.ai_energy_kwh(policy["elec_mult"]) * grid / 1000.0
                    * (1.0 + ZETA * shares[firm.sector]))
            nets.append(benefit - cost)

        replication_means.append(statistics.mean(nets))
        per_firm.extend(nets)

    return np.array(replication_means), np.array(per_firm)


def main():
    print("Uncertainty decomposition at 2040, baseline policy, zeta = 0.20")
    print(f"{'Country':<8}{'mean':>8} | {'AGENT HETEROGENEITY':>28} | {'MONTE CARLO':>26}")
    print(f"{'':8}{'':>8} | {'2.5th':>9}{'97.5th':>9}{'sd':>9} | "
          f"{'2.5th':>8}{'97.5th':>8}{'se':>9}")

    for country in COUNTRIES:
        means, firms = run(country)
        print(f"{country:<8}{means.mean():>8.2f} | "
              f"{np.percentile(firms, 2.5):>9.1f}{np.percentile(firms, 97.5):>9.1f}"
              f"{firms.std():>9.1f} | "
              f"{np.percentile(means, 2.5):>8.2f}{np.percentile(means, 97.5):>8.2f}"
              f"{means.std():>9.3f}")

    print()
    print("AGENT HETEROGENEITY = spread across the 40,000 individual firms.")
    print("MONTE CARLO        = spread of the 200 replication MEANS (simulation error).")
    print("They differ by roughly a factor of sqrt(200); reporting the second and")
    print("calling it the first overstates precision about individual firms and")
    print("understates the dispersion the agent loop actually generates.")


if __name__ == "__main__":
    main()
