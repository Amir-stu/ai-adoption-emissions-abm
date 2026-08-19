"""
Figure 5.1 -- adoption diffusion by sector (and a supplementary trajectory plot)
===============================================================================

Amir Ben Khadher, University of Mannheim. Support code for the bachelor thesis
"The Double-Edged Sword: AI Adoption, Labour Productivity, and Carbon Emissions".

Draws both figures from the unmodified model in model.py, at the same uniform
N = 200 replications used for every table in Chapter 6.

Outputs
    figures/fig5_1_adoption.png        Figure 5.1 of the thesis
    figures/fig5_2_net_trajectory.png  supplementary; not printed in the thesis
"""
import matplotlib.pyplot as plt
import seaborn as sns

from model import (
    GRID_FACTORS_0, SECTOR_NAMES, YEARS,
    run_scenario, run_scenario_sector_diffusion,
)
from paths import figures

sns.set_theme(style="whitegrid", font_scale=0.95)

N_MC = 200
COUNTRY_ORDER = sorted(GRID_FACTORS_0, key=GRID_FACTORS_0.get)
BASELINE = "Baseline (no policy)"


if __name__ == "__main__":
    # --- Figure 5.1: sector-level adoption diffusion -----------------------
    print("Figure 5.1: sector adoption diffusion (N = 200) ...")
    diffusion = run_scenario_sector_diffusion("EU", BASELINE, n_mc=N_MC)
    plt.figure(figsize=(8, 4.6))
    for color, sector in zip(sns.color_palette("viridis", len(SECTOR_NAMES)), SECTOR_NAMES):
        plt.plot(YEARS, diffusion[sector] * 100, color=color, linewidth=2, label=sector)
    plt.xlabel("Year")
    plt.ylabel("Adoption share $S_s(t)$ (% of agents in state P or F)")
    plt.legend(title="Sector", fontsize=8)
    plt.tight_layout()
    plt.savefig(figures("fig5_1_adoption.png"), dpi=300)
    plt.close()

    # --- Figure 5.2: net CO2 trajectory by country -------------------------
    print("Figure 5.2: net CO2 trajectory by country (N = 200) ...")
    plt.figure(figsize=(8, 4.6))
    for color, country in zip(sns.color_palette("crest", len(COUNTRY_ORDER)), COUNTRY_ORDER):
        res = run_scenario(country, BASELINE, n_mc=N_MC)
        plt.plot(YEARS, res["net_mean"], color=color, linewidth=2, label=country)
        plt.fill_between(YEARS, res["net_lo"], res["net_hi"], color=color, alpha=0.10)
        print(f"  {country}: net 2040 = {res['net_mean'][-1]:.1f} t/yr")
    plt.axhline(0, color="black", linewidth=1.0, linestyle="--")
    plt.xlabel("Year")
    plt.ylabel("Mean net CO$_2$ change per agent (t/yr)\n[>0 = benefit, <0 = cost]")
    plt.legend(title="Country / grid", fontsize=8)
    plt.tight_layout()
    plt.savefig(figures("fig5_2_net_trajectory.png"), dpi=300)
    plt.close()

    print("\nSaved: figures/fig5_1_adoption.png, figures/fig5_2_net_trajectory.png")
