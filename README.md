# AI Adoption, Labour Productivity, and Carbon Emissions

[![tests](https://github.com/Amir-stu/ai-adoption-emissions-abm/actions/workflows/tests.yml/badge.svg)](https://github.com/Amir-stu/ai-adoption-emissions-abm/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

Agent-based simulation code, raw output and figures for the bachelor thesis
**"The Double-Edged Sword: AI Adoption, Labour Productivity, and Carbon Emissions"**
(Amir Ben Khadher, University of Mannheim, 2026; supervisor Prof. Dr. Philipp Richter).

Every number, table and figure in Chapters 4–6 of the thesis is produced by the code
in `src/`. Nothing is computed by hand. Runs are deterministic, so the output
reproduces the printed values exactly rather than approximately.

![Structure of the agent-based model](figures/model_diagram.png)

*Full model description, in the ODD protocol: [`docs/model.md`](docs/model.md).*

---

## What the model does

The thesis asks whether AI adoption lowers a firm's carbon emissions, and answers
with a condition rather than a number. Emissions are an intensity multiplied by a
scale, so AI acts through two channels that must be separated: it lowers carbon
intensity by `γ`, and the same productivity gain may raise output by `g`. Emissions
after adoption are

```
E_new = E_base · (1 − γ·A) · (1 + g·A)
```

where `A` is the share of the firm's activity covered by AI. Benefit and cost are
therefore not independent, and the sign of the net effect turns on how much of the
productivity gain is converted into additional output — a pass-through no existing
study measures.

A population of 200 heterogeneous firm agents is simulated year by year from 2025 to
2040. Each agent draws its own sector, size, AI energy demand and adoption date
through a sector-specific hazard whose imitation term depends on the current adoption
share of its own sector. Population outcomes emerge from the loop over agents;
nothing is vectorised into a closed-form population equation.

Two things should be read together with the thesis, not separately from it:

- **This is not a causal estimate and not a forecast.** No parameter is identified at
  the level of the outcome it produces. The simulation is an accounting exercise that
  puts two separate literatures into one unit of account. Section 5.1 of the thesis
  says so.
- **The sign of the result is set by the parameters, not discovered by the model.**
  The informative part is the break-even analysis in `src/breakeven.py`, which asks
  how far each assumption can move before the conclusion reverses.

---

## Quick start

```bash
git clone https://github.com/Amir-stu/ai-adoption-emissions-abm.git
cd ai-adoption-emissions-abm
pip install -r requirements.txt
python run_all.py
```

`run_all.py` runs every script in dependency order and writes into `results/` and
`figures/`. A full regeneration takes about two minutes on a laptop: the factorial
design is 24 cells at N = 200 replications of 200 agents, and the break-even solver
re-runs the model at each solved root.

To regenerate a single exhibit, run its script directly — output paths are
resolved from the repository, not from the working directory:

```bash
python src/threshold.py
```

---

## Which script produces which exhibit

Chapter and exhibit numbers refer to the final, aligned version of the thesis.

| Thesis exhibit | Produced by | Output |
| --- | --- | --- |
| Table 4.1 — critical grid intensity `G*` by sector | `src/threshold.py` | `results/table4_1_threshold.csv` |
| Table 5.1 — baseline emissions per firm `E_base` | module constants in `src/model.py` (`SECTORS`) | — |
| Table 5.2 — parameters and provenance | module constants in `src/model.py` | — |
| Figure 5.1 — adoption diffusion by sector | `src/figures.py` | `figures/fig5_1_adoption.png` |
| Table 6.1 — net CO₂ by sector and rebound coefficient | `src/results_tables.py` | `results/table6_1_sector.csv`, `results/table6_1_rebound.csv` |
| Table 6.2 — net CO₂ by country and policy | `src/results_tables.py` | `results/table6_2_country_policy.csv` |
| Table 6.3 — break-even values | `src/breakeven.py` | `results/table6_3_breakeven.csv` |
| Table 6.4 — net CO₂ across output-scale scenarios `g` | `src/breakeven.py` | `results/table6_4_g_sweep.csv` |
| Table 6.5 — uncertainty decomposition | `src/uncertainty.py` | `results/table6_5_uncertainty.txt` |
| Figure 6.1 — break-even analysis | `src/figure_breakeven.py` | `figures/fig6_1_breakeven.png` |

Two images are not printed in the thesis: `figures/fig5_2_net_trajectory.png`,
supplementary output of `src/figures.py`, and `figures/model_diagram.png`, which
documents the code and is regenerated with it.

Parameter provenance — every constant, its source, and how to re-check it — is in
[`docs/parameters.md`](docs/parameters.md).

---

## Repository structure

```
.
|-- run_all.py                 regenerates every exhibit, in dependency order
|-- src/
|   |-- model.py               the model: Firm, FirmPopulation, the adoption hazard,
|   |                          the net-emissions identity, and every parameter
|   |-- experiment.py          the rebound extension and the factorial harness
|   |-- paths.py               output locations, resolved from the repository
|   |-- threshold.py           closed-form G* for a single firm     -> Table 4.1
|   |-- results_tables.py      the factorial design at N = 200      -> Tables 6.1, 6.2
|   |-- breakeven.py           the break-even solver, closed form   -> Tables 6.3, 6.4
|   |-- uncertainty.py         heterogeneity vs Monte Carlo error   -> Table 6.5
|   |-- figures.py             adoption and net-trajectory plots    -> Figure 5.1
|   |-- figure_breakeven.py    the break-even figure, printed size  -> Figure 6.1
|   `-- figure_model_diagram.py  the schematic shown above
|-- tests/                     the test suite (see below)
|-- results/                   CSV and text output of the scripts above
|-- figures/                   PNG and PDF figures
`-- docs/
    |-- model.md               the model in the ODD protocol
    `-- parameters.md          every parameter, its source, how to re-check it
```

`model.py` and `experiment.py` are libraries: importing them runs nothing. Every
exhibit is produced by an explicit script.

---

## Reproducibility

**Determinism.** Every run is seeded at 42, and each replication is seeded through
`zlib.crc32` of a fixed string rather than Python's salted `hash()`, so results do
not depend on `PYTHONHASHSEED`. Rerunning reproduces the committed CSVs byte for
byte.

**Self-verification.** `breakeven.py` re-runs the unmodified model at each solved
break-even value and reports the realised net effect at 2040, which returns to zero
to the fourth decimal place (`±0.0000 tCO₂/yr`).

**Common random numbers.** Neither the rebound coefficient `ζ` nor the output-scale
response `g` enters the seed, so every parameter value runs on the identical firm
population and the identical adoption path. The monotonicity of both sweeps
therefore holds by construction rather than up to sampling error.

**Tests.**

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers the mechanics of the agent and the population, the closed-form
break-even solutions against the simulation they claim to describe, and the
parameters against the values printed in the thesis — so that editing a constant
here without editing the thesis fails the build. It runs in a few seconds; CI runs
it on Python 3.11, 3.12 and 3.13.

---

## Known limits of the model

These are properties of the model, not defects, and Section 6.4 of the thesis
discusses each:

- **Operational carbon only.** Embodied emissions from GPU fabrication and
  data-centre construction are not represented, so every net benefit here is an
  upper bound and every net cost a lower one.
- **Scope 3 is excluded on both sides**, and Scope 2 is modelled from sector-average
  electricity and a national average grid factor rather than observed at the firm.
- **The carbon-intensity coefficient `γ` is transferred** from Chinese listed firms,
  and from a revenue-denominated intensity, to a European emissions stock.
- **Output expansion `g` is a scenario, not an observation.** It is swept, not
  estimated; the pass-through from productivity gains to output is the quantity the
  thesis identifies as decisive and unmeasured.
- **Data-centre siting is not modelled.** `G_c(t)` is a national average, but AI
  workloads run in data centres whose grid mix can differ from it.
- **Water and land are excluded.**
- **Adoption responds neither to the grid nor to electricity prices.**

---

## Requirements

Python 3.11+ and the packages in `requirements.txt`. There are no external data
dependencies: every parameter is either taken from a cited source, calibrated to a
documented pattern, or flagged as a scenario in Table 5.2 of the thesis.
[`docs/parameters.md`](docs/parameters.md) records where each value comes from.

---

## Citation

If you use this code, please cite the thesis it supports. Machine-readable metadata
is in [`CITATION.cff`](CITATION.cff).

> Ben Khadher, A. (2026). *The Double-Edged Sword: AI Adoption, Labour Productivity,
> and Carbon Emissions.* Bachelor's thesis, University of Mannheim.

## Licence

MIT — see [`LICENSE`](LICENSE). Academic use, please cite the thesis.
