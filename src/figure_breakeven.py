"""Figure 6.1 -- break-even analysis, drawn at final printed size.

Replaces the previous image, which (a) rendered a literal LaTeX escape in its
title and (b) was labelled for the abandoned single-elasticity formulation.

Inputs are the values reported in the thesis and verified against the closed
form of Equations (4.2) and (4.3): gamma* from Table 6.3, net(g) from Table 6.4.
Net(g) is exactly linear in g, so the panel (b) lines are drawn through the
tabulated points rather than re-simulated.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from paths import figures

GAMMA_CENTRAL = 2.3          # transferred benchmark, Zhou and Bu (2026)
G_DAGGER = 2.3404            # gamma / (1 - gamma*A), A = 0.75
G_CEILING = 4.0              # scenario ceiling, Aldasoro et al. (2026)

COUNTRIES = ["France", "EU", "US", "China", "Poland"]
GAMMA_STAR = {"France": 0.37, "EU": 0.81, "US": 1.11, "China": 1.16, "Poland": 1.55}
NET = {  # g = 0, 1, 2, 4 per cent
    "France": [5.29, 2.59, -0.11, -5.50],
    "EU":     [7.03, 2.40, -2.23, -11.49],
    "US":     [9.55, 1.66, -6.23, -22.00],
    "China":  [14.50, 1.99, -10.51, -35.52],
    "Poland": [6.69, -2.05, -10.80, -28.28],
}
G_POINTS = np.array([0.0, 1.0, 2.0, 4.0])

# Colourblind-safe, and separated in lightness so the figure survives greyscale
COLOURS = {"France": "#4C9F70", "EU": "#3B7EA1", "US": "#8C6BB1",
           "China": "#C1553B", "Poland": "#5B5B5B"}
STYLES = {"France": "-", "EU": "--", "US": "-.", "China": ":", "Poland": (0, (3, 1, 1, 1))}

# Drawn at final printed size (textwidth = 15.7 cm = 6.18 in) so the figure is
# included at width=\textwidth with no rescaling and the point sizes below are
# the point sizes on the printed page.
plt.rcParams.update({
    "font.family": "serif", "font.size": 8,
    "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.edgecolor": "#333333", "axes.linewidth": 0.7,
    "grid.color": "#CCCCCC", "grid.linewidth": 0.4,
})

fig, axes = plt.subplots(1, 2, figsize=(6.18, 2.95))

# ---- (a) break-even intensity reduction against the transferred benchmark ----
ax = axes[0]
order = sorted(COUNTRIES, key=lambda c: GAMMA_STAR[c])
vals = [GAMMA_STAR[c] for c in order]
ax.barh(order, vals, color=[COLOURS[c] for c in order], height=0.60, zorder=3)
for y, v in enumerate(vals):
    ax.text(v + 0.06, y, f"{v:.2f}%", va="center", fontsize=7, zorder=4)
ax.axvline(GAMMA_CENTRAL, color="black", linestyle="--", linewidth=1.0, zorder=2)
ax.text(GAMMA_CENTRAL - 0.08, 0.28, "benchmark $\\gamma = 2.3\\%$",
        rotation=90, ha="right", va="bottom", fontsize=7, color="black")
ax.set_xlim(0, 2.75)
ax.set_xlabel("Break-even reduction $\\gamma^{*}$ (%)")
ax.set_title("(a) How far the benchmark can fall\nbefore the net effect reaches zero")
ax.grid(axis="x", zorder=0)
ax.set_axisbelow(True)

# ---- (b) net effect across the output-scale response --------------------------
ax = axes[1]
gg = np.linspace(0, G_CEILING, 200)
for c in COUNTRIES:
    slope = NET[c][0] - NET[c][1]          # per percentage point, exactly linear
    ax.plot(gg, NET[c][0] - slope * gg, linestyle=STYLES[c], color=COLOURS[c],
            linewidth=1.3, label=c, zorder=3)
    ax.plot(G_POINTS, NET[c], "o", color=COLOURS[c], markersize=2.6, zorder=4)

ax.axhline(0, color="black", linewidth=0.9, zorder=2)
ax.axvline(G_DAGGER, color="#B03030", linestyle=":", linewidth=1.2, zorder=2)
ax.text(G_DAGGER + 0.10, 12.2, "$g^{\\dagger} = 2.34\\%$",
        fontsize=7, color="#B03030", va="top")
ax.set_xlim(0, G_CEILING)
ax.set_xlabel("Output-scale response $g$ (%)")
ax.set_ylabel("Net operational $\\mathrm{CO_2}$ at 2040 (t/yr)")
ax.set_title("(b) The second edge: the output-scale response\n"
             "(ceiling $g = 4\\%$ from the productivity premium)")
ax.legend(frameon=False, fontsize=7, loc="lower left", handlelength=2.4,
          labelspacing=0.3)
ax.grid(zorder=0)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig(figures("fig6_1_breakeven.png"), dpi=300)
print("wrote figures/fig6_1_breakeven.png")
