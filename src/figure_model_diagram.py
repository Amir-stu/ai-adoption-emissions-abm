"""
Schematic of the agent-based model (documentation figure)
=========================================================

Draws the structure of the simulation defined in `model.py`: what each agent is
initialised with, what happens to it in one simulated year, where the feedback
loop is, and which thesis exhibit each emergent aggregate becomes.

This figure documents the code; it is not a result and is not printed in the
thesis. It is regenerated with the rest of the repository so that it cannot
drift away from the implementation it describes.

Outputs: figures/model_diagram.png, figures/model_diagram.pdf
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from paths import figures

# Dark palette, in the register of a code editor: the diagram documents source
# code and is read next to it.
BACKGROUND = "#0D1117"   # page
PANEL = "#161B22"        # panel fill
SHADE = "#12171E"        # fill of the annual-loop container
BORDER = "#30363D"       # panel borders
INK = "#E6EDF3"          # body text
MUTED = "#8B949E"        # secondary text, thin rules
BENEFIT = "#2DD4BF"      # the productivity channel (emissions down)
COST = "#F0883E"         # the AI energy channel (emissions up)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "mathtext.fontset": "dejavusans",
    "text.color": INK,
    "figure.facecolor": BACKGROUND,
    "savefig.facecolor": BACKGROUND,
})

# Column geometry, in the 0-100 data coordinates used throughout.
COL1 = (1.5, 25.2)       # initialisation panel: x, width
LOOP = (27.0, 48.0)      # annual-loop container
BOX = (30.5, 36.0)       # boxes inside the container
COL3 = (76.3, 22.7)      # outputs panel
FEEDBACK_X = 70.5        # corridor for the sector-share feedback loop
YEAR_X = 29.3            # corridor for the year loop


def panel(ax, x, y, w, h, *, fill=PANEL, edge=BORDER, lw=1.1, radius=1.2, z=2):
    """A rounded rectangle in data coordinates."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0,rounding_size=%.2f" % radius,
        facecolor=fill, edgecolor=edge, linewidth=lw, zorder=z,
    ))


def heading(ax, x, y, text, colour=INK, size=9.5):
    ax.text(x, y, text, color=colour, fontsize=size, fontweight="bold",
            va="top", ha="left", zorder=4)


def body(ax, x, y, lines, size=7.7, colour=INK, leading=2.80):
    """Left-aligned block of text lines. Returns the y of the last line."""
    for i, line in enumerate(lines):
        ax.text(x, y - i * leading, line, color=colour, fontsize=size,
                va="top", ha="left", zorder=4)
    return y - (len(lines) - 1) * leading


def segment(ax, start, end, *, colour=MUTED, lw=1.2, head=False, dashed=False, z=3):
    """A straight connector, optionally with an arrow head at `end`."""
    ax.add_patch(FancyArrowPatch(
        start, end,
        arrowstyle="-|>" if head else "-",
        mutation_scale=11, color=colour, linewidth=lw, zorder=z,
        shrinkA=0, shrinkB=0,
        linestyle=(0, (4, 2)) if dashed else "solid",
    ))


def build():
    fig, ax = plt.subplots(figsize=(13.0, 7.4))
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(BACKGROUND)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(1.5, 98.0, "Agent-based model of AI adoption and firm emissions",
            fontsize=13, fontweight="bold", color=INK, va="top", ha="left")
    ax.text(1.5, 93.8,
            "One replication: 200 firm agents advanced year by year from 2025 to 2040. "
            "Every population outcome is a sum over agents, not a closed-form population equation.",
            fontsize=8.6, color=MUTED, va="top", ha="left")

    # ------------------------------------------------------------------
    # 1. Initialisation
    # ------------------------------------------------------------------
    panel(ax, COL1[0], 28.0, COL1[1], 58.0)
    heading(ax, COL1[0] + 1.7, 84.0, "1  INITIALISATION  (t = 2025)")
    ax.text(COL1[0] + 1.7, 80.4, r"drawn once per agent $i = 1,\ldots,200$",
            fontsize=7.7, color=MUTED, va="top", ha="left")
    body(ax, COL1[0] + 1.7, 75.4, [
        r"sector $s_i$: uniform over 6 sectors",
        r"size: 45% small, 36% medium, 18% large",
        "",
        "carbon-intensity gain",
        r"   $\gamma_i = 0.023$   medium and large firms",
        r"   $\gamma_i = 0$        small firms",
        "",
        "AI electricity, as a share of own use",
        r"   partial  $kWh_i \sim U(0.5\%,\,1.5\%)\cdot elec_s$",
        r"   full      $kWh_i \sim U(1.5\%,\,4.0\%)\cdot elec_s$",
        "",
        "baseline emissions, Eq. (5.6)",
        r"   $E_{base,i} = S^{(1)}_s I_c + elec_s\,G_c(0)/1000$",
        "",
        r"initial state  $a_i = N$  (non-adopter)",
    ])
    ax.text(COL1[0] + 1.7, 29.6,
            "Each agent owns its own draws. Nothing is\n"
            "shared, averaged or vectorised across firms.",
            fontsize=7.4, color=MUTED, va="bottom", ha="left", linespacing=1.5)

    # ------------------------------------------------------------------
    # 2. The annual loop
    # ------------------------------------------------------------------
    panel(ax, LOOP[0], 12.5, LOOP[1], 73.5, fill=SHADE, edge=BORDER, lw=1.0, z=1)
    heading(ax, BOX[0], 84.0, "2  ANNUAL LOOP  (t = 2025 … 2040)")
    ax.text(BOX[0], 80.4, "each agent is evaluated independently, once per simulated year",
            fontsize=7.7, color=MUTED, va="top", ha="left")

    # 2a. adoption decision
    panel(ax, BOX[0], 58.0, BOX[1], 20.0, edge=BENEFIT)
    heading(ax, BOX[0] + 1.7, 76.2, "a.  Adoption decision", colour=BENEFIT, size=9.0)
    body(ax, BOX[0] + 1.7, 72.4, [
        r"hazard   $h_i(t) = p_s + q_s\,S_s(t)$",
        r"draw  $u \sim U(0,1)$;   if  $u < h_i(t)$  the agent advances  $N \rightarrow P \rightarrow F$",
        r"adoption intensity  $A(a_i) \in \{0,\;0.375,\;0.75\}$",
    ], size=8.1, leading=3.4)
    ax.text(BOX[0] + 1.7, 59.4,
            "Bass (1969) form, carried as a behavioural assumption",
            fontsize=7.2, color=MUTED, va="bottom", ha="left")

    # 2b. emissions accounting
    panel(ax, BOX[0], 33.0, BOX[1], 20.0, edge=COST)
    heading(ax, BOX[0] + 1.7, 51.2, "b.  Net emissions of the year, Eq. (5.5)",
            colour=COST, size=9.0)
    ax.text(BOX[0] + BOX[1] / 2 + 0.6, 46.2,
            r"$Net_i(t) = E_{base,i}\,[\,1-(1-\gamma_i A)(1+gA)\,] \; - \; "
            r"kWh_i\,(1+\zeta S_s(t))\,G_c(t)\,/\,1000$",
            fontsize=7.8, color=INK, va="center", ha="center", zorder=4)
    segment(ax, (38.6, 44.3), (38.6, 42.6), colour=BENEFIT, lw=0.9)
    segment(ax, (58.8, 44.3), (58.8, 42.6), colour=COST, lw=0.9)
    ax.text(38.6, 42.0,
            "productivity channel\n"
            r"intensity falls by $\gamma$, output rises by $g$",
            fontsize=7.3, color=BENEFIT, va="top", ha="center", linespacing=1.45, zorder=4)
    ax.text(58.8, 42.0,
            "AI energy cost\n"
            "own electricity, priced at its grid",
            fontsize=7.3, color=COST, va="top", ha="center", linespacing=1.45, zorder=4)
    ax.text(BOX[0] + BOX[1] / 2, 34.4,
            r"The sign turns on which term is larger; the model does not settle that.",
            fontsize=7.4, color=MUTED, va="bottom", ha="center")

    # 2c. environment
    panel(ax, BOX[0], 15.0, BOX[1], 11.0, edge=BORDER)
    heading(ax, BOX[0] + 1.7, 24.2, "c.  Environment", colour=MUTED, size=9.0)
    body(ax, BOX[0] + 1.7, 20.6, [
        r"grid decarbonises:  $G_c(t) = G_c(0)\,(1-\delta_c)^{\,t}$",
        "a policy regime may cap the grid factor or halve AI electricity",
    ], size=7.9)

    # internal arrows
    segment(ax, (48.5, 58.0), (48.5, 53.0), colour=INK, head=True, lw=1.1)
    ax.text(49.2, 55.5, r"state $a_i(t)$", fontsize=7.3, color=MUTED,
            va="center", ha="left")
    segment(ax, (42.0, 26.0), (42.0, 33.0), colour=INK, head=True, lw=1.1)
    ax.text(42.7, 29.5, r"$G_c(t)$", fontsize=7.3, color=MUTED,
            va="center", ha="left")

    # feedback: the sector adoption share re-enters both the hazard and the
    # rebound multiplier. This is the model's only feedback loop.
    x_end = BOX[0] + BOX[1]
    segment(ax, (x_end, 61.0), (FEEDBACK_X, 61.0), colour=BENEFIT, lw=1.2, dashed=True)
    segment(ax, (FEEDBACK_X, 61.0), (FEEDBACK_X, 74.0), colour=BENEFIT, lw=1.2, dashed=True)
    segment(ax, (FEEDBACK_X, 74.0), (x_end, 74.0), colour=BENEFIT, lw=1.2,
            dashed=True, head=True)
    segment(ax, (FEEDBACK_X, 61.0), (FEEDBACK_X, 40.5), colour=COST, lw=1.2, dashed=True)
    segment(ax, (FEEDBACK_X, 40.5), (x_end, 40.5), colour=COST, lw=1.2,
            dashed=True, head=True)
    ax.text(FEEDBACK_X + 1.1, 68.0, r"$S_s(t)$: peer imitation",
            fontsize=7.4, color=BENEFIT, va="center", ha="center", rotation=90)
    ax.text(FEEDBACK_X + 1.1, 51.0, r"$S_s(t)$: rebound",
            fontsize=7.4, color=COST, va="center", ha="center", rotation=90)

    # the year loop
    segment(ax, (BOX[0], 20.5), (YEAR_X, 20.5), colour=MUTED, lw=1.1)
    segment(ax, (YEAR_X, 20.5), (YEAR_X, 74.0), colour=MUTED, lw=1.1)
    segment(ax, (YEAR_X, 74.0), (BOX[0], 74.0), colour=MUTED, lw=1.1, head=True)
    ax.text(YEAR_X - 1.0, 47.0, r"next year  $t \rightarrow t+1$",
            fontsize=7.4, color=MUTED, va="center", ha="center", rotation=90)

    # ------------------------------------------------------------------
    # 3. Emergent aggregates
    # ------------------------------------------------------------------
    panel(ax, COL3[0], 28.0, COL3[1], 58.0)
    heading(ax, COL3[0] + 1.7, 84.0, "3  EMERGENT AGGREGATES")
    ax.text(COL3[0] + 1.7, 80.4, "averaged over 200 independent replications",
            fontsize=7.7, color=MUTED, va="top", ha="left")
    body(ax, COL3[0] + 1.7, 75.4, [
        r"adoption S-curves  $S_s(t)$",
        r"     $\rightarrow$ Figure 5.1",
        "",
        r"net CO$_2$ at 2040 by sector and $\zeta$",
        r"     $\rightarrow$ Table 6.1",
        "",
        r"net CO$_2$ at 2040 by country $\times$ policy",
        r"     $\rightarrow$ Table 6.2",
        "",
        r"break-even $\gamma^{*}$, $g^{*}$, $\zeta^{*}$: closed form,",
        "verified against the model",
        r"     $\rightarrow$ Tables 6.3, 6.4 and Figure 6.1",
        "",
        "heterogeneity vs Monte Carlo error",
        r"     $\rightarrow$ Table 6.5",
    ])

    # column connectors
    segment(ax, (COL1[0] + COL1[1], 57.0), (LOOP[0], 57.0), colour=INK, lw=1.4, head=True)
    segment(ax, (LOOP[0] + LOOP[1], 57.0), (COL3[0], 57.0), colour=INK, lw=1.4, head=True)

    # ------------------------------------------------------------------
    # Experimental design strip
    # ------------------------------------------------------------------
    panel(ax, 1.5, 2.5, 97.0, 8.0, fill=SHADE, edge=BORDER, lw=1.0)
    heading(ax, 3.2, 9.4, "EXPERIMENTAL DESIGN", size=8.6)
    ax.text(3.2, 6.0,
            r"5 country grids  $\times$  4 policy regimes  $\times$  4 rebound "
            r"coefficients $\zeta$  $\times$  4 output-scale scenarios $g$"
            "          200 agents $\\times$ 200 replications per cell"
            r"          common random numbers across $\zeta$ and $g$"
            "          seed 42, CRC-32 stream keys",
            fontsize=8.0, color=INK, va="top", ha="left")

    fig.tight_layout(pad=0.4)
    return fig


if __name__ == "__main__":
    figure = build()
    figure.savefig(figures("model_diagram.png"), dpi=300, facecolor=BACKGROUND)
    figure.savefig(figures("model_diagram.pdf"), facecolor=BACKGROUND)
    print("wrote figures/model_diagram.png and figures/model_diagram.pdf")
