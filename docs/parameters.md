# Parameters and provenance

Every parameter in `src/model.py`, its value, its source, and how to re-check it.
This document is the long form of Table 5.2 of the thesis; the grouping is the
identification status used there, and it is the order in which the results should
be doubted.

| Group | Meaning |
| --- | --- |
| A. Measured | taken from an emissions, energy or grid account |
| B. Measured | firm population structure |
| C. Transferred | estimated in another setting; could be wrong by a factor |
| D. Calibrated | benchmarked to a published pattern, not observed at the firm |
| E. Scenario | not an estimate at all; swept, and the sign of the result turns on it |

`tests/test_thesis_values.py` asserts the values below against the code, so the
two cannot drift apart silently.

---

## A. Measured

### Grid carbon intensity `G_c(0)` — kgCO₂e/kWh, 2024

| France | EU-27 | US | China | Poland |
| --- | --- | --- | --- | --- |
| 0.04048 | 0.21120 | 0.38378 | 0.55540 | 0.60818 |

Source. Ember, *Yearly Electricity Data* (2024 values), republished by Our World
in Data: <https://ourworldindata.org/grapher/carbon-intensity-electricity>

**How to re-check.** Download the CSV and filter `Year = 2024`. Read the CSV, not a
rendered chart: during this work the US value came back three different ways
(389.02, 413.75, 457.44) before the CSV was parsed directly.

### Grid decarbonisation `δ_c` — annual rate of decline

| France | EU-27 | US | China | Poland |
| --- | --- | --- | --- | --- |
| 2.51% | 4.73% | 3.17% | 2.20% | 3.22% |

Source. The annualised 2014→2024 decline in the same Ember/OWID series,
`1 − (v₂₀₂₄/v₂₀₁₄)^(1/10)`.

Why it matters. These rates reverse which grid is dirtiest by 2040: Poland
starts dirtier, but decarbonises faster, so China becomes the binding case. A
uniform decarbonisation assumption hides that. The ten-year rate is used rather
than the five-year, because France's five-year figure (7.50%) is distorted by the
recovery from the 2022 nuclear outages.

### Baseline emissions `E_base` — tCO₂e/yr per enterprise, EU-27

| Sector | Scope 1 | Scope 2 | Total |
| --- | --- | --- | --- |
| ICT | 83 | 185 | 268 |
| Electronics & Pharma | 400 | 528 | 928 |
| Manufacturing | 2,066 | 528 | 2,594 |
| Transport & Storage | 3,970 | 194 | 4,164 |
| Finance | 347 | 209 | 556 |
| Accommodation & Food | 61 | 74 | 135 |

Enterprises with ten or more persons employed. Scope 2 is not stored as a constant:
it is computed per country as the firm's own electricity priced at its own grid, so
a firm on a coal grid carries the Scope 2 burden of that grid on both sides of
Eq. (5.5).

Sources — all Eurostat, EU-27, via the dissemination API:

- Scope 1: `env_ac_ainah_r2`, `airpol = CO2`, `unit = THS_T`, 2023
- Electricity: `env_ac_pefasu`, `prod_nrg = P26`, `stk_flow = USE`, `unit = TJ`, 2022,
  converted at 1 TJ = 277,778 kWh
- Denominator: `sbs_sc_ovw`, `indic_sbs = ENT_NR`, `size_emp ∈ {10-19, 20-49, 50-249, GE250}`, 2022

**NACE mapping.** ICT = J · Electronics & Pharma = C21+C26+C27 · Manufacturing = C
minus those · Transport & Storage = H · Finance = K · Accommodation & Food = I

**Two judgment calls**, neither of them a free parameter:

1. the ≥10-employee frame, to match the EIBIS sampling frame and exclude micro firms;
2. PEFA carries no C21/C26/C27 detail, so manufacturing electricity is allocated
   pro rata per enterprise across C.

Why Scope 2 is in the baseline.The cost side of Eq. (5.5) is electricity × grid
intensity, which is a Scope 2 quantity. Setting it against a Scope 1 benefit alone
would compare two different accounting boundaries. Eurostat's air emissions accounts
attribute purchased-electricity emissions to NACE D rather than to the consuming
sector, so Scope 2 has to be added back.

### Firm electricity use — kWh/yr per enterprise

ICT 876,614 · Electronics & Pharma and Manufacturing 2,501,164 · Transport & Storage
920,755 · Finance 989,556 · Accommodation & Food 348,027. Same PEFA ÷ SBS sources as
above.

---

## B. Measured — firm population structure

Firm-size shares.45% small, 36% medium, 18% large, from the EIBIS distribution
reported by Aldasoro et al. (2026). The code draws from an eleven-element tuple
(5/4/2), i.e. 45.5 / 36.4 / 18.2%.

---

## C. Transferred — estimated in another setting

### Carbon-intensity reduction `γ = 0.023`

**Source.** Zhou & Bu (2026), *Energies* 19(3):821, doi:10.3390/en19030821. Chinese
A-share listed firms, 2012–2024, firm and year fixed effects, IV and a dynamic event
study: −2.0% energy, −1.8% energy intensity, −2.3% carbon emission intensity within
two to three years of adoption. Effects concentrate in large, non-state and
technology-intensive firms.

How it is used. As a *transferred benchmark*, not a European estimate: it is
identified on Chinese firms, on a revenue-denominated intensity, with adoption
proxied by capital intensity. Medium and large firms carry it; small firms take the
point estimate implied by an insignificant coefficient, which is zero. It is not
drawn from a distribution, because no standard error was reported for the quantity
actually used here.

**What depends on it.** Section 6.2 reports the break-even `γ*` — how far this value
would have to fall before the net effect vanishes — rather than treating it as
secure.

### Rebound coefficient `ζ ∈ {0, 0.10, 0.20, 0.30}`

Source. Sorrell, Dimitropoulos & Sommerville (2009), *Energy Policy*,
doi:10.1016/j.enpol.2008.11.026: direct rebound in road transport, 10–12% in the
short run and 26–29% in the long run, from the best-studied case. No AI-specific
estimate exists, which is why `ζ` is swept and why Table 6.3 reports the `ζ*` at
which the net effect vanishes instead of asserting a value.

### National Scope 1 scaling `I_c`

France 0.69 · EU 1.00 · US 1.62 · China 2.71 · Poland 1.60 — each country's CO₂
intensity of GDP relative to the EU (Our World in Data, 2023). An economy-wide
proxy applied to a sector-level quantity, and therefore transferred rather than
measured.

---

## D. Calibrated — benchmarked, not observed at the firm

### AI electricity, as a share of the firm's own use

Partial adopter `U(0.5%, 1.5%)`, full adopter `U(1.5%, 4.0%)`.

Anchor. IEA, *Energy and AI* (2025): data centres consumed roughly 415 TWh in
2024, about 1.5% of world electricity, rising towards 3% by 2030; AI is 5–15% of
data-centre load now, projected at 35–50% by 2030. AI therefore approaches 1–1.5% of
all electricity by 2030, concentrated in adopters — so an adopting firm sits above
that economy-wide mean, which is the range above.
<https://www.iea.org/reports/energy-and-ai>

### Adoption intensity `A(N/P/F) = 0 / 0.375 / 0.75`

Source. McKinsey, *The State of AI: Global Survey* (2025): 88% of organisations
use AI in at least one business function, and adopters average three functions.
Three of eight functions is 0.375; a full adopter is set at six of eight.

Caveat. The function count is measured; the step from a function count to a share
of a firm's *emissions-generating activity* is an interpretation. That is why this
sits in group D and not in group A.

### Bass coefficients `p_s ∈ [0.010, 0.050]`, `q_s ∈ [0.18, 0.40]`

Set ordinally to the EIBIS sectoral adoption gradient (large firms ≈45%, small ≈24%).
The *ranking* of sectors is calibrated; the timing and the shape of each curve are
consequences of the assumption, not evidence for it.

---

## E. Scenario — not an estimate

### Output-scale response `g ∈ {0, 0.01, 0.02, 0.04}`

The proportional expansion of output that accompanies adoption. No study reports it.
The ceiling of the envelope is the +4% labour-productivity premium that Aldasoro et
al. (2026, EIB WP 2026/02) identify for European adopters using matched EIBIS–ORBIS
data on more than twelve thousand non-financial firms, instrumenting European
adoption with the adoption rates of US peers. That premium *bounds* the pass-through
rather than measuring it.

This is the parameter the thesis identifies as decisive and unmeasured: the
break-even `g*` lies between 0.77% and 1.96% across the five grids, inside the range
the European productivity estimate makes plausible.

---

## Model rules that are not parameters

1. A renewable mandate is a ceiling, not a replacement. `min(G_c(t), ceiling)`.
   Applied unconditionally it would *raise* emissions on a grid already cleaner than
   the floor — which is exactly what happened to France in an earlier draft of
   Table 6.2.
2. The combined-policy adoption boost is an internal benchmark, not a free
   parameter. Every firm adopts on the coefficients of the fastest sector actually
   observed in the EIBIS gradient (ICT), so no value has to be chosen.
3. The seed includes the policy name. Two numerically identical policy cells
   therefore differ by roughly ±1 tCO₂/yr at N = 200. Differences below about
   1.5 tCO₂/yr between policy cells are simulation noise, not policy effects.
