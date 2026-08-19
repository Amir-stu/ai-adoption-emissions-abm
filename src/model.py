"""
The agent-based model (thesis Chapter 5)
========================================

Amir Ben Khadher, University of Mannheim. Support code for the bachelor thesis
"The Double-Edged Sword: AI Adoption, Labour Productivity, and Carbon Emissions".

This module is the model. It is a library: it defines the agent, the population
and the accounting identity, and it runs nothing on import. The scripts that
produce the thesis exhibits import from here (see run_all.py).

WHAT MAKES IT AGENT-BASED
    Every firm is an independent object (class Firm) with its own state, its own
    random draws and its own update. The adoption S-curve, the energy-demand path
    and the net carbon balance are not written down as population equations: they
    emerge from the loop over independent agents in FirmPopulation.step(). Nothing
    is vectorised into a closed-form population expression.

THE TWO CHANNELS (thesis Section 5.2)
    Emissions are an intensity multiplied by a scale, so adoption acts twice:
    it lowers carbon intensity by gamma, and the same productivity gain may raise
    output by g. Emissions after adoption are therefore

        E_new = E_base * (1 - gamma*A) * (1 + g*A)                    Eq. (5.3)

    with A the share of the firm's activity covered by AI. The net effect per firm
    and year, Eq. (5.5), subtracts the AI energy cost from that saving. Its sign
    is set by which of the two channels is larger, and the model does not settle
    that question; the break-even analysis in breakeven.py is what does the work.

PARAMETER PROVENANCE (thesis Table 5.2; docs/parameters.md)
    Aldasoro et al. (2026), EIB WP 2026/02  -- +4% labour productivity for European
                                               adopters, driven by capital deepening;
                                               EIBIS firm-size adoption gradient
    Zhou & Bu (2026), Energies 19(3):821    -- carbon-intensity reduction gamma = 0.023,
                                               concentrated in large and technology-
                                               intensive firms
    Ember / Our World in Data (2024)        -- national grid intensities and the
                                               annualised 2014-2024 decarbonisation rate
    Eurostat (2022, 2023)                   -- Scope 1 emissions and electricity use
                                               per enterprise, by sector
    IEA (2025), Energy and AI               -- AI electricity as a share of firm use
    Sorrell et al. (2009)                   -- direct rebound, the range zeta is swept over
    Bass (1969)                             -- innovation/imitation diffusion form

Determinism: every replication is seeded through zlib.crc32 of a fixed key rather
than Python's salted hash(), so results do not depend on PYTHONHASHSEED and the
committed CSVs reproduce byte for byte.
"""

import random
import statistics
import zlib

import numpy as np

SEED = 42

T_START, T_END = 2025, 2040
T_YEARS = T_END - T_START + 1
YEARS = list(range(T_START, T_END + 1))

N_FIRMS = 200          # agents per country population, per replication
N_MC = 200             # independent replications per scenario (uniform across Ch.6-7)

# ---------------------------------------------------------------------------
# 1. SECTORS  (heterogeneous Bass coefficients and baseline emissions)
# ---------------------------------------------------------------------------
SECTORS = {
    # scope1   : MEASURED tonnes CO2/yr per enterprise (>=10 persons employed),
    #            EU-27. Eurostat air emissions accounts (env_ac_ainah_r2, 2023)
    #            divided by Eurostat SBS enterprise counts (sbs_sc_ovw, 2022).
    # elec_kwh : MEASURED total electricity use per enterprise, EU-27. Eurostat
    #            physical energy flow accounts (env_ac_pefasu, P26, USE, 2022).
    # Scope 2 is NOT stored: it is computed per country as elec_kwh * G_c(0),
    # so a firm on a coal grid carries the Scope 2 burden of that grid.
    "ICT":                  {"scope1":   83, "elec_kwh":   876_614, "p": 0.050, "q": 0.40},
    "Electronics & Pharma": {"scope1":  400, "elec_kwh": 2_501_164, "p": 0.040, "q": 0.35},
    "Manufacturing":        {"scope1": 2_066, "elec_kwh": 2_501_164, "p": 0.030, "q": 0.30},
    "Transport & Storage":  {"scope1": 3_970, "elec_kwh":   920_755, "p": 0.025, "q": 0.28},
    "Finance":              {"scope1":  347, "elec_kwh":   989_556, "p": 0.035, "q": 0.32},
    "Accommodation & Food": {"scope1":   61, "elec_kwh":   348_027, "p": 0.010, "q": 0.18},
}

# Country scaling of Scope 1. The Eurostat baseline is European; applying it
# unchanged to US, Chinese and Polish firms would assert that a manufacturing
# firm emits the same wherever it operates. Scope 1 is therefore scaled by each
# country's CO2 intensity of GDP relative to the EU (Our World in Data, "Annual
# CO2 emissions per GDP", 2023). This is an economy-wide proxy, not a
# sector-specific one, and is treated as TRANSFERRED, not measured.
CO2_INTENSITY_REL_EU = {
    "France": 0.69, "EU": 1.00, "US": 1.62, "China": 2.71, "Poland": 1.60,
}

# ---------------------------------------------------------------------------
# THE PRODUCTIVITY CHANNEL: gamma, and the output-expansion offset g
# ---------------------------------------------------------------------------
# gamma = AI-induced reduction in CARBON EMISSION INTENSITY (emissions per unit
#   of output). Zhou & Bu (2026), Energies 19(3):821, doi:10.3390/en19030821 --
#   Chinese A-share listed firms 2012-2024, firm and year fixed effects, IV and
#   a dynamic event study: -2.0% energy, -1.8% energy intensity, -2.3% carbon
#   emission intensity within 2-3 years of adoption. Effects concentrate in
#   large, non-state and technology-intensive firms.
GAMMA = 0.023

# OUTPUT_EXPANSION (g) = the proportional rise in output that accompanies the
#   productivity gain. Because gamma is an INTENSITY coefficient and Eq. (5.1)
#   multiplies it by an ABSOLUTE emissions stock, the benefit is only
#   E_base*A*gamma when output is held fixed. In general
#       dE ~ E_base * A * (g - gamma),
#   so the realised benefit is E_base * A * (gamma - g).
#   Aldasoro et al. (2026), EIB WP 2026/02 / BIS WP 1325, find +4% labour
#   productivity for European adopters driven by CAPITAL DEEPENING with NO
#   adverse employment effect -- i.e. output expands rather than labour
#   contracting. g is therefore swept on [0, 0.04], and gamma < 0.04 means the
#   productivity channel can turn from a sink into a source.
OUTPUT_EXPANSION = 0.00

AI_SHARE_PARTIAL = (0.005, 0.015)
AI_SHARE_FULL    = (0.015, 0.040)

SECTOR_NAMES = list(SECTORS.keys())

# ---------------------------------------------------------------------------
# 2. COUNTRIES / GRID  (kg CO2/kWh at t=2025; decarbonising thereafter)
# ---------------------------------------------------------------------------
GRID_FACTORS_0 = {
    # EXACT 2024 values, Ember Yearly Electricity Data via Our World in Data,
    # parsed directly from the published CSV (not transcribed by hand).
    "France":  0.04048,
    "EU":      0.21120,
    "US":      0.38378,
    "China":   0.55540,
    "Poland":  0.60818,
}

# Country-specific grid decarbonisation, measured as the annualised rate of
# decline in the SAME series over 2014-2024, replacing the uniform 3% guess.
GRID_DECARB = {
    "France": 0.0251, "EU": 0.0473, "US": 0.0317,
    "China":  0.0220, "Poland": 0.0322,
}

DECARB_RATE = 0.03   # retained only as the default for callers that omit a rate

# ---------------------------------------------------------------------------
# 3. POLICY REGIMES (the four regimes crossed in the design, Section 5.3.1)
# ---------------------------------------------------------------------------
POLICY_SCENARIOS = {
    "Baseline (no policy)":      {"grid_override": None, "elec_mult": 1.0, "phi_boost": 0.00, "fastest": False},
    "Renewable Energy Mandate":  {"grid_override": 0.04048, "elec_mult": 1.0, "phi_boost": 0.00, "fastest": False},
    "AI Efficiency Standard":    {"grid_override": None, "elec_mult": 0.5, "phi_boost": 0.00, "fastest": False},
    "Combined Policy":           {"grid_override": 0.04048, "elec_mult": 0.5, "phi_boost": 0.00, "fastest": True},
}

# ---------------------------------------------------------------------------
# 4. THE FIRM AGENT
# ---------------------------------------------------------------------------

class Firm:
    """
    A single, independent agent. Each Firm instance owns its own state and
    its own random draws -- nothing about its behaviour is shared or
    vectorised across the population.

    The adoption state a_i maps to an adoption intensity A (Table 5.2):
    A(N) = 0, A(P) = 0.375, A(F) = 0.75, i.e. three and six of the eight
    business functions of McKinsey's State of AI (2025).
    """
    __slots__ = ("agent_id", "sector", "size", "state", "gamma", "kwh_p", "kwh_f", "e_base")

    STATE_N, STATE_P, STATE_F = 0, 1, 2
    A_OF_STATE = (0.00, 0.375, 0.75)   # 3 of 8 / 6 of 8 business functions
    SIZE_SHARES = ("small", "small", "small", "small", "small",  # 5 of 11 = 45%
                   "medium", "medium", "medium", "medium",       # 4 of 11 = 36%
                   "large", "large")                             # 2 of 11 = 18%

    def __init__(self, agent_id, sector, rng, country="EU"):
        self.agent_id = agent_id
        self.sector = sector
        self.size = rng.choice(Firm.SIZE_SHARES)   # EIBIS firm-size population shares
        self.state = Firm.STATE_N
        self.gamma = self._assign_gamma()
        elec = SECTORS[sector]["elec_kwh"]
        self.kwh_p = rng.uniform(*AI_SHARE_PARTIAL) * elec
        self.kwh_f = rng.uniform(*AI_SHARE_FULL) * elec
        # Baseline emissions = country-scaled Scope 1 + country-specific Scope 2.
        scope1 = SECTORS[sector]["scope1"] * CO2_INTENSITY_REL_EU[country]
        scope2 = elec * GRID_FACTORS_0[country] / 1000.0
        self.e_base = scope1 + scope2

    def _assign_gamma(self):
        """
        Firm-level AI-induced carbon-intensity reduction.

        Both verified sources agree that the effect concentrates in larger
        firms: Aldasoro et al. (2026) find the productivity premium in medium
        and large firms only, and Zhou & Bu (2026) report stronger effects for
        large, non-state and technology-intensive firms. Small firms therefore
        take the point estimate implied by an insignificant coefficient, zero.

        gamma is a published point estimate, so it is NOT drawn from a
        distribution. The earlier N(mu, sigma^2) specification manufactured
        dispersion from a standard error that was never reported for the
        quantity actually used.
        """
        return 0.0 if self.size == "small" else GAMMA

    def maybe_adopt(self, hazard, rng):
        """Each firm independently draws against its own adoption hazard."""
        if self.state < Firm.STATE_F and rng.random() < hazard:
            self.state += 1

    def benefit_fraction(self):
        """
        EXACT emissions reduction as a fraction of the baseline stock.

        Emissions after adoption are the product of a lower intensity and a
        larger output:
            E_new = E_base * (1 - gamma*A) * (1 + g*A)
        so the reduction, as a fraction of E_base, is
            1 - (1 - gamma*A)(1 + g*A) = A*(gamma - g) + gamma*g*A^2 .
        The final term is the interaction that a first-order expansion drops;
        it is retained here so the identity is exact rather than approximate.
        The expression remains linear in gamma and in g, so the closed-form
        break-even solutions of breakeven.py are unaffected.

        Small firms have no estimated productivity premium, so they receive
        neither an intensity gain nor an output expansion.
        """
        if self.gamma == 0.0:
            return 0.0
        a = Firm.A_OF_STATE[self.state]
        return 1.0 - (1.0 - self.gamma * a) * (1.0 + OUTPUT_EXPANSION * a)

    def ai_energy_kwh(self, elec_mult):
        if self.state == Firm.STATE_P:
            return self.kwh_p * elec_mult
        if self.state == Firm.STATE_F:
            return self.kwh_f * elec_mult
        return 0.0

    def net_co2(self, grid_intensity, elec_mult):
        """Net_i(t) = E_base,i * [1-(1-gamma*A)(1+g*A)] - kWh_i * G(t)/1000."""
        benefit = self.e_base * self.benefit_fraction()
        cost = self.ai_energy_kwh(elec_mult) * grid_intensity / 1000.0
        return benefit - cost


# ---------------------------------------------------------------------------
# 5. THE FIRM POPULATION (the model itself)
# ---------------------------------------------------------------------------

class FirmPopulation:
    """
    A population of independent Firm agents for one country. Diffusion
    (Section 5.4) operates WITHIN sectors: a firm's adoption hazard
    depends on the share of its own sector's peers who have already
    adopted, S_sector(t), not on an economy-wide average -- this is an
    explicit modelling choice reflecting sector-specific peer effects.
    """

    def __init__(self, n_firms, rng, country="EU"):
        self.country = country
        self.firms = []
        for i in range(n_firms):
            sector = rng.choice(SECTOR_NAMES)
            self.firms.append(Firm(i, sector, rng, country))
        self._by_sector = {s: [f for f in self.firms if f.sector == s] for s in SECTOR_NAMES}

    def adoption_share(self):
        return sum(f.state > 0 for f in self.firms) / len(self.firms)

    def sector_adoption_share(self, sector):
        group = self._by_sector[sector]
        if not group:
            return 0.0
        return sum(f.state > 0 for f in group) / len(group)

    def step(self, phi_boost, rng, fastest=False):
        """One annual update: every firm independently evaluates its own
        sector-specific hazard and may advance one state.

        Under `fastest`, every firm adopts on the hazard of the fastest
        sector actually observed in the EIBIS gradient (ICT). This replaces
        the earlier free `phi_boost` with an internal benchmark: no value is
        chosen, the fastest observed rate is simply applied to all."""
        sector_shares = {s: self.sector_adoption_share(s) for s in SECTOR_NAMES}
        p_max = max(SECTORS[s]["p"] for s in SECTOR_NAMES)
        q_max = max(SECTORS[s]["q"] for s in SECTOR_NAMES)
        for firm in self.firms:
            p_s = p_max if fastest else SECTORS[firm.sector]["p"]
            q_s = q_max if fastest else SECTORS[firm.sector]["q"]
            hazard = p_s + q_s * sector_shares[firm.sector] + phi_boost
            firm.maybe_adopt(hazard, rng)

    def aggregate_net(self, grid_intensity, elec_mult):
        nets = [f.net_co2(grid_intensity, elec_mult) for f in self.firms]
        return statistics.mean(nets)


def deterministic_seed(*parts):
    """
    A reproducible replacement for Python's built-in hash() on strings/tuples.
    hash() of str/tuple objects is salted with a per-process random value
    (PYTHONHASHSEED) unless explicitly disabled, so seeding Random() with
    hash(...) gives a DIFFERENT stream on every run -- silently breaking the
    "fixed seed -> reproducible results" claim. zlib.crc32 on a fixed string
    encoding is stable across processes and Python versions.
    """
    key = "|".join(str(p) for p in parts).encode("utf-8")
    return zlib.crc32(key)


def grid_intensity_at(t_idx, grid0, grid_override, decarb_rate=DECARB_RATE):
    g = grid0 * (1.0 - decarb_rate) ** t_idx
    if grid_override is not None:
        # A mandate is a CEILING: it can only clean a grid, never dirty one.
        # The previous unconditional override made the Renewable Mandate
        # RAISE emissions on grids already cleaner than the floor (visible in
        # the published Table 6.2, where France falls 73.0 -> 70.5).
        return min(g, grid_override)
    return g


def run_one_replication(country, policy, n_firms, rng):
    """One full agent-based run: build a fresh population, advance it
    T_YEARS times, and record the trajectories that emerge."""
    pop = FirmPopulation(n_firms, rng, country)
    grid0 = GRID_FACTORS_0[country]
    adoption_traj, net_traj = [], []
    sector_traj = {s: [] for s in SECTOR_NAMES}
    for t_idx in range(T_YEARS):
        pop.step(policy["phi_boost"], rng, policy.get("fastest", False))
        G_t = grid_intensity_at(t_idx, grid0, policy["grid_override"], GRID_DECARB[country])
        net_traj.append(pop.aggregate_net(G_t, policy["elec_mult"]))
        adoption_traj.append(pop.adoption_share())
        for s in SECTOR_NAMES:
            sector_traj[s].append(pop.sector_adoption_share(s))
    return adoption_traj, net_traj, sector_traj


def run_scenario_sector_diffusion(country, policy_name, n_firms=N_FIRMS, n_mc=N_MC, base_seed=SEED):
    """Same agent-based machinery as run_scenario, but tracking the
    emergent adoption share within each sector (diffusion is sector-driven
    in this model -- see Section 5.4)."""
    policy = POLICY_SCENARIOS[policy_name]
    all_sector = {s: np.zeros((n_mc, T_YEARS)) for s in SECTOR_NAMES}
    for r in range(n_mc):
        rng = random.Random(deterministic_seed(country, policy_name, "sector", r, base_seed))
        _, _, sector_traj = run_one_replication(country, policy, n_firms, rng)
        for s in SECTOR_NAMES:
            all_sector[s][r] = sector_traj[s]
    return {s: all_sector[s].mean(axis=0) for s in SECTOR_NAMES}


def run_scenario(country, policy_name, n_firms=N_FIRMS, n_mc=N_MC, base_seed=SEED):
    """N_MC independent agent-based replications for one (country, policy) cell."""
    policy = POLICY_SCENARIOS[policy_name]
    all_adopt = np.zeros((n_mc, T_YEARS))
    all_net = np.zeros((n_mc, T_YEARS))
    for r in range(n_mc):
        rng = random.Random(deterministic_seed(country, policy_name, r, base_seed))
        adopt_traj, net_traj, _ = run_one_replication(country, policy, n_firms, rng)
        all_adopt[r] = adopt_traj
        all_net[r] = net_traj
    return {
        "adopt_mean": all_adopt.mean(axis=0),
        "adopt_lo": np.percentile(all_adopt, 2.5, axis=0),
        "adopt_hi": np.percentile(all_adopt, 97.5, axis=0),
        "net_mean": all_net.mean(axis=0),
        "net_lo": np.percentile(all_net, 2.5, axis=0),
        "net_hi": np.percentile(all_net, 97.5, axis=0),
    }


def tipping_year(net_mean):
    for t_idx, v in enumerate(net_mean):
        if v < 0:
            return T_START + t_idx
    return None
