"""
The factorial harness with the rebound term (thesis Chapter 6)
==============================================================

Amir Ben Khadher, University of Mannheim. Support code for the bachelor thesis
"The Double-Edged Sword: AI Adoption, Labour Productivity, and Carbon Emissions".

This module extends the agent and population of model.py with the one term the
model itself leaves out: the rebound coefficient zeta of Eq. (5.5). It is a
library, imported by results_tables.py; it runs nothing on import.

THE REBOUND TERM
    As adoption spreads, the effective cost of an AI-assisted task falls and its
    volume expands, offsetting part of the efficiency gain (Jevons; Sorrell,
    Dimitropoulos & Sommerville 2009). It enters as a multiplier on each firm's
    AI electricity demand, scaling with the current adoption share of the firm's
    own sector:

        kWh_i(state, t) = kWh_i(state) * elec_mult * (1 + zeta * S_s(t))

    with zeta swept over {0.00, 0.10, 0.20, 0.30}; zeta = 0 reproduces model.py
    exactly. No AI-specific rebound estimate exists, so zeta is swept rather than
    calibrated, and Table 6.3 reports the zeta* at which the net effect vanishes.

THE DESIGN (thesis Section 5.3.1)
    5 country grids x 4 policy regimes x 4 rebound coefficients, each cell run for
    N_MC independent replications of N_FIRMS agents. Sector is not a further
    dimension: it is already a per-agent attribute, so sector results are read off
    the same population runs by grouping agents ex post.

COMMON RANDOM NUMBERS
    zeta is deliberately kept out of the seed, so every rebound level reuses the
    identical firm population and the identical adoption path. zeta then perturbs
    only the cost term, which makes the net effect monotonically non-increasing in
    zeta by construction rather than up to sampling noise.
"""

import random
import statistics

import numpy as np

from model import (
    Firm, SECTORS, SECTOR_NAMES, GRID_FACTORS_0, GRID_DECARB, POLICY_SCENARIOS,
    T_START, T_YEARS, N_FIRMS, grid_intensity_at, deterministic_seed,
)

SEED = 42
N_MC = 200                                # replications per (country, policy, zeta) cell
ZETA_VALUES = [0.00, 0.10, 0.20, 0.30]    # rebound coefficients swept in Table 6.1


# ---------------------------------------------------------------------------
# REBOUND-AWARE AGENT AND POPULATION (extends the Firm/FirmPopulation of model.py)
# ---------------------------------------------------------------------------

class ReboundFirm(Firm):
    """Identical to the Firm agent of model.py, but its energy demand can be
    scaled by a rebound multiplier that depends on its own sector's current
    adoption share (computed by the population, not by the firm itself)."""
    __slots__ = ()

    def net_co2_rebound(self, grid_intensity, elec_mult, rebound_mult):
        benefit = self.e_base * self.benefit_fraction()
        cost = self.ai_energy_kwh(elec_mult) * rebound_mult * grid_intensity / 1000.0
        return benefit - cost


class ReboundPopulation:
    """Same mechanics as FirmPopulation (sector-driven diffusion), with
    rebound-aware net-CO2 accounting."""

    def __init__(self, n_firms, rng, country="EU"):
        self.country = country
        self.firms = []
        for i in range(n_firms):
            sector = rng.choice(SECTOR_NAMES)
            self.firms.append(ReboundFirm(i, sector, rng, country))
        self._by_sector = {s: [f for f in self.firms if f.sector == s] for s in SECTOR_NAMES}

    def sector_adoption_share(self, sector):
        group = self._by_sector[sector]
        return 0.0 if not group else sum(f.state > 0 for f in group) / len(group)

    def adoption_share(self):
        return sum(f.state > 0 for f in self.firms) / len(self.firms)

    def step(self, phi_boost, rng, fastest=False):
        sector_shares = {s: self.sector_adoption_share(s) for s in SECTOR_NAMES}
        p_max = max(SECTORS[s]["p"] for s in SECTOR_NAMES)
        q_max = max(SECTORS[s]["q"] for s in SECTOR_NAMES)
        for firm in self.firms:
            if fastest:
                p_s, q_s = p_max, q_max
            else:
                p_s, q_s = SECTORS[firm.sector]["p"], SECTORS[firm.sector]["q"]
            hazard = p_s + q_s * sector_shares[firm.sector] + phi_boost
            firm.maybe_adopt(hazard, rng)

    def aggregate_net(self, grid_intensity, elec_mult, zeta):
        sector_shares = {s: self.sector_adoption_share(s) for s in SECTOR_NAMES}
        nets = [
            f.net_co2_rebound(grid_intensity, elec_mult, 1.0 + zeta * sector_shares[f.sector])
            for f in self.firms
        ]
        return statistics.mean(nets)

    def sector_net(self, grid_intensity, elec_mult, zeta):
        sector_shares = {s: self.sector_adoption_share(s) for s in SECTOR_NAMES}
        out = {}
        for s in SECTOR_NAMES:
            group = self._by_sector[s]
            if not group:
                out[s] = 0.0
                continue
            rebound_mult = 1.0 + zeta * sector_shares[s]
            out[s] = statistics.mean(f.net_co2_rebound(grid_intensity, elec_mult, rebound_mult) for f in group)
        return out


def run_one_replication(country, policy, zeta, n_firms, rng):
    pop = ReboundPopulation(n_firms, rng, country)
    grid0 = GRID_FACTORS_0[country]
    net_traj = []
    sector_net_traj = {s: [] for s in SECTOR_NAMES}
    for t_idx in range(T_YEARS):
        pop.step(policy["phi_boost"], rng, policy.get("fastest", False))
        G_t = grid_intensity_at(t_idx, grid0, policy["grid_override"], GRID_DECARB[country])
        net_traj.append(pop.aggregate_net(G_t, policy["elec_mult"], zeta))
        sec_net = pop.sector_net(G_t, policy["elec_mult"], zeta)
        for s in SECTOR_NAMES:
            sector_net_traj[s].append(sec_net[s])
    return net_traj, sector_net_traj


def run_cell(country, policy_name, zeta, n_firms=N_FIRMS, n_mc=N_MC, base_seed=SEED):
    policy = POLICY_SCENARIOS[policy_name]
    all_net = np.zeros((n_mc, T_YEARS))
    all_sector_net = {s: np.zeros((n_mc, T_YEARS)) for s in SECTOR_NAMES}
    for r in range(n_mc):
        # COMMON RANDOM NUMBERS: zeta is deliberately NOT in the seed, so every
        # rebound level reuses the identical firm population and the identical
        # adoption path. zeta then perturbs only the cost term, which makes
        # Net(zeta) monotonically non-increasing by construction rather than
        # up to sampling noise.
        rng = random.Random(deterministic_seed(country, policy_name, r, base_seed))
        net_traj, sector_net_traj = run_one_replication(country, policy, zeta, n_firms, rng)
        all_net[r] = net_traj
        for s in SECTOR_NAMES:
            all_sector_net[s][r] = sector_net_traj[s]
    return {
        "net_mean": all_net.mean(axis=0),
        "net_lo": np.percentile(all_net, 2.5, axis=0),
        "net_hi": np.percentile(all_net, 97.5, axis=0),
        "sector_net_mean": {s: all_sector_net[s].mean(axis=0) for s in SECTOR_NAMES},
    }


def tipping_year(net_mean):
    for t_idx, v in enumerate(net_mean):
        if v < 0:
            return T_START + t_idx
    return None
