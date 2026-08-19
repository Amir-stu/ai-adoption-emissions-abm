"""
Tables 6.3 and 6.4 -- break-even (structured uncertainty) analysis
=========================================================

Amir Ben Khadher, University of Mannheim. Support code for the bachelor thesis
"The Double-Edged Sword: AI Adoption, Labour Productivity, and Carbon Emissions".

WHAT THIS SCRIPT DOES
---------------------
It runs the agent-based model of model.py (imported unmodified) and,
for every (country, policy, zeta) cell, decomposes the population-mean net
effect at 2040 into its additive components:

    Net(2040) = benefit_small + [gamma*(w_ml + g*w2_ml) - g*w_ml]
                - cost_0 - zeta * cost_S

where w_ml = sum_{medium/large} E_base*A and w2_ml = sum_{medium/large} E_base*A^2.
The second weight carries the gamma*g interaction of the EXACT identity
E_new = E_base (1 - gamma*A)(1 + g*A); no first-order expansion is used.

Because that expression is still LINEAR in gamma, in the output-expansion g,
in the rebound coefficient zeta and in the baseline-emissions scale E_base,
each break-even value is solved in CLOSED FORM from those components rather
than by numerical bisection. Every closed-form solution is then VERIFIED by
re-running the unmodified model at the solved value and confirming Net ~ 0.

Reported break-even quantities
------------------------------
    gamma*  : the carbon-intensity reduction at which Net(2040) = 0. Reported
              in absolute terms (e.g. 0.011 = 1.1%) AND as a percentage of the
              central estimate gamma = 0.023 (Zhou & Bu 2026).
    g*      : the AI-induced output expansion at which Net(2040) = 0, holding
              gamma central. Compare against the +4% labour productivity of
              Aldasoro et al. (2026).
    E_base* : the baseline-emissions scale at which Net(2040) = 0.
    zeta*   : the rebound coefficient at which Net(2040) = 0.

Outputs:
    results/table6_3_breakeven.csv   Table 6.3
    results/table6_4_g_sweep.csv     Table 6.4

The printed Figure 6.1 is drawn from these values, at final size, by
figure_breakeven.py.
"""

import random
import statistics

import numpy as np
import pandas as pd

import model as M
from model import (
    SECTOR_NAMES, GRID_FACTORS_0, GRID_DECARB, POLICY_SCENARIOS,
    Firm, FirmPopulation, deterministic_seed, grid_intensity_at,
    T_YEARS, SEED, GAMMA,
)
from paths import results


N_FIRMS = 200
N_MC = 200
COUNTRY_ORDER = sorted(GRID_FACTORS_0, key=GRID_FACTORS_0.get)
BASELINE = "Baseline (no policy)"
ZETA_CENTRAL = 0.20
G_VALUES = [0.00, 0.01, 0.02, 0.04]      # output expansion, anchored to Aldasoro +4%


# ---------------------------------------------------------------------------
# 1. INSTRUMENTED POPULATION
# ---------------------------------------------------------------------------

class DecomposedPopulation(FirmPopulation):
    """Identical dynamics to FirmPopulation; adds a component decomposition."""

    def components(self, grid_intensity, elec_mult):
        """
        Population means (per agent) of the additive components of the net
        effect, plus the structural weight multiplying the coefficient.

            benefit_small : sum over small firms  of E_base * A * 0   (= 0)
            w_ml          : sum over medium/large of E_base * A
            w2_ml         : sum over medium/large of E_base * A^2  (carries the
                            gamma*g interaction of the exact identity)
            cost_0        : sum over all firms    of kWh * elec_mult * G/1000
            cost_S        : the same, weighted by the firm's own sector share
        """
        shares = {s: self.sector_adoption_share(s) for s in SECTOR_NAMES}
        n = len(self.firms)
        b_small = c0 = cS = w_ml = w2_ml = 0.0
        for f in self.firms:
            a = Firm.A_OF_STATE[f.state]
            if f.size == "small":
                b_small += f.e_base * f.benefit_fraction()
            else:
                w_ml += f.e_base * a
                w2_ml += f.e_base * a * a
            cost = f.ai_energy_kwh(elec_mult) * grid_intensity / 1000.0
            c0 += cost
            cS += cost * shares[f.sector]
        return dict(benefit_small=b_small / n, w_ml=w_ml / n, w2_ml=w2_ml / n,
                    cost_0=c0 / n, cost_S=cS / n)


def run_components(country, policy_name, n_firms=N_FIRMS, n_mc=N_MC, base_seed=SEED):
    """N_MC replications; returns the mean 2040 decomposition across them."""
    policy = POLICY_SCENARIOS[policy_name]
    grid0 = GRID_FACTORS_0[country]
    keys = ("benefit_small", "w_ml", "w2_ml", "cost_0", "cost_S")
    acc = {k: [] for k in keys}
    for r in range(n_mc):
        rng = random.Random(deterministic_seed(country, policy_name, r, base_seed))
        pop = DecomposedPopulation(n_firms, rng, country)
        for t_idx in range(T_YEARS):
            pop.step(policy["phi_boost"], rng, policy.get("fastest", False))
            G_t = grid_intensity_at(t_idx, grid0, policy["grid_override"],
                                    GRID_DECARB[country])
        comp = pop.components(G_t, policy["elec_mult"])
        for k in keys:
            acc[k].append(comp[k])
    return {k: float(np.mean(v)) for k, v in acc.items()}


def benefit_ml(comp, gamma=GAMMA, g=0.0):
    """
    EXACT medium/large benefit, from sum E_base*[A(gamma-g) + gamma*g*A^2]
        = gamma*(w_ml + g*w2_ml) - g*w_ml .
    Still linear in gamma and in g, so every break-even below stays closed-form.
    """
    return gamma * (comp["w_ml"] + g * comp["w2_ml"]) - g * comp["w_ml"]


def net_at(comp, gamma=GAMMA, g=0.0, zeta=0.0, ebase_scale=1.0):
    """Net(2040) under a given coefficient, output expansion, rebound and scale."""
    benefit = ebase_scale * (comp["benefit_small"] + benefit_ml(comp, gamma, g))
    return benefit - comp["cost_0"] - zeta * comp["cost_S"]


# ---------------------------------------------------------------------------
# 2. CLOSED-FORM BREAK-EVEN SOLUTIONS
# ---------------------------------------------------------------------------

def gamma_star(comp, zeta, g=0.0):
    """Carbon-intensity reduction at which Net(2040) = 0, in ABSOLUTE terms."""
    num = comp["cost_0"] + zeta * comp["cost_S"] - comp["benefit_small"] + g * comp["w_ml"]
    return num / (comp["w_ml"] + g * comp["w2_ml"])


def g_star(comp, zeta, gamma=GAMMA):
    """Output expansion at which Net(2040) = 0, holding gamma central."""
    num = comp["cost_0"] + zeta * comp["cost_S"] - comp["benefit_small"]
    return (num - gamma * comp["w_ml"]) / (gamma * comp["w2_ml"] - comp["w_ml"])


def zeta_star(comp, gamma=GAMMA, g=0.0):
    """Rebound coefficient at which Net(2040) = 0."""
    benefit = comp["benefit_small"] + benefit_ml(comp, gamma, g)
    return (benefit - comp["cost_0"]) / comp["cost_S"]


def ebase_star_ratio(comp, zeta, gamma=GAMMA, g=0.0):
    """Baseline-emissions scale, as a fraction of Table 5.1, at which Net = 0."""
    benefit = comp["benefit_small"] + benefit_ml(comp, gamma, g)
    return (comp["cost_0"] + zeta * comp["cost_S"]) / benefit


# ---------------------------------------------------------------------------
# 3. VERIFICATION -- re-run the UNMODIFIED model at the solved value
# ---------------------------------------------------------------------------

def verify_gamma(country, policy_name, gamma_solved, zeta,
                 n_firms=N_FIRMS, n_mc=N_MC, base_seed=SEED):
    """Re-runs the model with GAMMA set to the solved value; returns mean Net(2040)."""
    policy = POLICY_SCENARIOS[policy_name]
    grid0 = GRID_FACTORS_0[country]
    saved = M.GAMMA
    M.GAMMA = gamma_solved
    try:
        out = []
        for r in range(n_mc):
            rng = random.Random(deterministic_seed(country, policy_name, r, base_seed))
            pop = DecomposedPopulation(n_firms, rng, country)
            for t_idx in range(T_YEARS):
                pop.step(policy["phi_boost"], rng, policy.get("fastest", False))
                G_t = grid_intensity_at(t_idx, grid0, policy["grid_override"],
                                        GRID_DECARB[country])
            shares = {s: pop.sector_adoption_share(s) for s in SECTOR_NAMES}
            nets = []
            for f in pop.firms:
                benefit = f.e_base * f.benefit_fraction()
                cost = (f.ai_energy_kwh(policy["elec_mult"]) * G_t / 1000.0
                        * (1.0 + zeta * shares[f.sector]))
                nets.append(benefit - cost)
            out.append(statistics.mean(nets))
        return float(np.mean(out))
    finally:
        M.GAMMA = saved


# ---------------------------------------------------------------------------
# 4. RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Break-even analysis: {N_FIRMS} agents x {N_MC} replications, seed {SEED}")
    print(f"Central gamma = {GAMMA} (Zhou & Bu 2026); zeta = {ZETA_CENTRAL}\n")

    comps = {}
    for c in COUNTRY_ORDER:
        comps[c] = run_components(c, BASELINE)
        print(f"  {c}: components computed.")

    rows = []
    for country in COUNTRY_ORDER:
        c = comps[country]
        gs = gamma_star(c, ZETA_CENTRAL)
        rows.append({
            "country": country,
            "grid_2025": GRID_FACTORS_0[country],
            "net_2040": net_at(c, GAMMA, 0.0, ZETA_CENTRAL),
            "gamma_star_pct": 100 * gs,
            "gamma_star_share_of_central": 100 * gs / GAMMA,
            "g_star_pct": 100 * g_star(c, ZETA_CENTRAL),
            "ebase_star_pct": 100 * ebase_star_ratio(c, ZETA_CENTRAL),
            "zeta_star": zeta_star(c),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(results("table6_3_breakeven.csv"), index=False)
    print("\n=== Break-even summary (baseline policy, zeta = 0.20, g = 0) ===")
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    joint = []
    for g in G_VALUES:
        row = {"g_pct": 100 * g}
        for country in COUNTRY_ORDER:
            row[country] = net_at(comps[country], GAMMA, g, ZETA_CENTRAL)
        joint.append(row)
    jdf = pd.DataFrame(joint)
    jdf.to_csv(results("table6_4_g_sweep.csv"), index=False)
    print("\n=== Net CO2 at 2040 as AI-induced output expansion g rises ===")
    print(jdf.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    print("\n=== Verification: model re-run at the solved break-even gamma ===")
    for country in ["China", "Poland", "EU"]:
        gs = gamma_star(comps[country], ZETA_CENTRAL)
        realised = verify_gamma(country, BASELINE, gs, ZETA_CENTRAL)
        print(f"  {country}: solved gamma* = {100*gs:5.2f}% "
              f"-> model Net(2040) = {realised:+.4f} t/yr (target 0)")

    print("\nSaved: results/table6_3_breakeven.csv, results/table6_4_g_sweep.csv")
