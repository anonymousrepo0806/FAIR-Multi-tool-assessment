import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans",
                     "axes.linewidth": 0.5, "pdf.fonttype": 42})
PAIRS = ["FC vs FU", "FC vs KG", "FU vs KG"]
KEYS = ["FC-FU", "FC-KG", "FU-KG"]
PAIR_COLOR = ["#6250d6", "#e87ba4", "#008300"]
CMAP = "RdBu_r"
NORM = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
ORDER = ["BLOD", "CHeCLOUD", "Cross-domain", "Geography", "Government", "Life Sciences",
         "Linguistic", "Media", "Publications", "Social Networking", "User Generated"]
DIM_NAMES = {"F": "Findability", "A": "Accessibility", "I": "Interoperability",
             "R": "Reusability", "composite": "Composite"}

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "results", "agreement_all.csv")
if not os.path.exists(SRC):
    sys.exit(f"{SRC} not found. Run merge.py and raw_analysis.py first.")
df = pd.read_csv(SRC)


def rho_row(sub):
    sub = sub.set_index("pair")
    return [float(sub.loc[k, "rho"]) if k in sub.index and pd.notna(sub.loc[k, "rho"]) else np.nan for k in KEYS]


sc = df[(df.level == "sub-cloud") & (df.dim == "composite")]
clouds = [c for c in ORDER if c in set(sc.group)] + sorted(set(sc.group) - set(ORDER))
sub_rho = np.array([rho_row(sc[sc.group == c]) for c in clouds])
sub_n = np.array([int(sc[sc.group == c]["n"].max()) for c in clouds])

po = df[df.level == "pooled"]
dims = [d for d in DIM_NAMES if d in set(po.dim)]
dim_rho = np.array([rho_row(po[po.dim == d]) for d in dims])


def heat(ax, M, rows):
    im = ax.imshow(np.ma.masked_invalid(M), cmap=CMAP, norm=NORM, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if np.isnan(M[i, j]):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                           hatch="////", lw=0, ec="0.6"))
    ax.set_xticks(range(3), PAIRS)
    ax.set_yticks(range(len(rows)), rows)
    ax.tick_params(length=0)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    return im


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, f"{name}.pdf"))
    fig.savefig(os.path.join(HERE, f"{name}.png"), dpi=200)


fig, ax = plt.subplots(figsize=(3.33, 3.0))
im = heat(ax, sub_rho, clouds)
fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(0.4)
save(fig, "fig_subcloud_heatmap")

fig, ax = plt.subplots(figsize=(3.33, 1.7))
im = heat(ax, dim_rho, [DIM_NAMES[d] for d in dims])
if "composite" in dims:
    ax.axhline(len(dims) - 1.5, color="black", lw=0.8)
fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(0.4)
save(fig, "fig_dimension_heatmap")

pooled = dim_rho[dims.index("composite")]
fig, ax = plt.subplots(figsize=(3.33, 1.9))
for j, pair in enumerate(PAIRS):
    ok = ~np.isnan(sub_rho[:, j])
    rs, ns = sub_rho[ok, j], sub_n[ok]
    if len(rs) == 0:
        print(f"{pair}: no defined sub-cloud correlations, skipped")
        continue
    wmean = float((rs * ns).sum() / ns.sum())
    ax.scatter(rs, np.full(len(rs), j) + np.random.default_rng(j).uniform(-.12, .12, len(rs)),
               s=np.sqrt(ns) * 1.8, c=PAIR_COLOR[j], alpha=.7, lw=0.4, edgecolors="white", zorder=2)
    ax.plot([pooled[j]] * 2, [j - .34, j + .34], color="#1a1a1a", lw=1.8, zorder=3)
    ax.plot([wmean] * 2, [j - .34, j + .34], color=PAIR_COLOR[j], lw=1.8, ls="--", zorder=3)
    print(f"{pair}: pooled={pooled[j]:+.3f}  weighted within={wmean:+.3f}  "
          f"range=[{rs.min():+.3f},{rs.max():+.3f}]")
ax.axvline(0, color="0.8", lw=0.5, zorder=1)
ax.set_yticks(range(3), PAIRS)
lo = min(-0.5, np.nanmin(sub_rho) - 0.05)
ax.set_xlim(lo, 1.05)
ax.invert_yaxis()
ax.set_xlabel("Spearman ρ")
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
save(fig, "fig_pooled_vs_within")
print(f"Figures written to {HERE}")
