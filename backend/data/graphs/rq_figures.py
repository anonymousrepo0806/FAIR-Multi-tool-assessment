import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from style import TOOL_COLOR, SEQUENTIAL, UP, DOWN, INK, MUTED, GRID, apply, light

apply()
TOOLS = ["FAIR-Checker", "F-UJI", "KGHeartBeat"]
PRINCIPLES = ["F1", "F2", "F3", "A1", "A1.2", "I1", "I2", "I3", "R1.1", "R1.2", "R1.3"]
ORDER = ["BLOD", "CHeCLOUD", "Cross-domain", "Geography", "Government", "Life Sciences",
         "Linguistic", "Media", "Publications", "Social Networking", "User Generated"]
BINS = np.linspace(0, 1, 21)


def unique_assessments(df):
    df = df.copy()
    df["_o"] = df["subcloud"].map({s: i for i, s in enumerate(ORDER)}).fillna(99)
    first = df.sort_values("_o").drop_duplicates("dataset_id")[["dataset_id", "subcloud"]]
    return df.merge(first, on=["dataset_id", "subcloud"]).drop(columns="_o")


def save(fig, out, name):
    fig.savefig(os.path.join(out, f"{name}.pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(out, f"{name}.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def slug(x):
    return str(x).replace(" ", "_").replace("/", "-")


def clean(ax):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.4)
    ax.set_axisbelow(True)


def heat(ax, M, rows, cols):
    im = ax.imshow(np.ma.masked_invalid(M), cmap=SEQUENTIAL, vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if np.isnan(M[i, j]):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, hatch="////", lw=0, ec=MUTED))
    ax.set_xticks(range(len(cols)), cols)
    ax.set_yticks(range(len(rows)), rows)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    return im


def boxes(ax, vals_by_pos, color, width):
    pos = [p for p, v in vals_by_pos if len(v)]
    vals = [v for p, v in vals_by_pos if len(v)]
    if not vals:
        return
    ax.boxplot(vals, positions=pos, widths=width, showfliers=False, patch_artist=True,
               boxprops=dict(facecolor=light(color), edgecolor=color, lw=0.7),
               medianprops=dict(color=color, lw=1.4), whiskerprops=dict(color=color, lw=0.7),
               capprops=dict(color=color, lw=0.7))
    ax.scatter(pos, [np.mean(v) for v in vals], s=9, c=INK, marker="D", zorder=3, lw=0)


def principle_axes(ax, principles):
    ax.set_ylim(-0.05, 1.05)
    ax.set_yticks([0, 0.5, 1])
    ax.set_xticks(range(len(principles)), principles)
    ax.set_xlim(-0.6, len(principles) - 0.4)
    ax.set_xlabel("FAIR principle")
    ax.set_ylabel("Normalized score")
    clean(ax)


def grouped_principle_boxes(data, tools, principles, out, name):
    fig, ax = plt.subplots(figsize=(7.0, 2.0))
    w = 0.8 / len(tools)
    for i, t in enumerate(tools):
        g = data[data.tool == t]
        off = (i - (len(tools) - 1) / 2) * w
        boxes(ax, [(k + off, g[p].dropna().values) for k, p in enumerate(principles)], TOOL_COLOR[t], w * 0.85)
    principle_axes(ax, principles)
    fig.tight_layout()
    save(fig, out, name)


def single_principle_boxes(data, tool, principles, out, name):
    fig, ax = plt.subplots(figsize=(3.33, 1.6))
    g = data[data.tool == tool]
    boxes(ax, [(k, g[p].dropna().values) for k, p in enumerate(principles)], TOOL_COLOR[tool], 0.55)
    for k, p in enumerate(principles):
        if g[p].dropna().empty:
            ax.axvspan(k - .4, k + .4, color=GRID, lw=0)
    principle_axes(ax, principles)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    fig.tight_layout()
    save(fig, out, name)


def overlay_hist(values_by_tool, out, name, size=(3.33, 1.8)):
    fig, ax = plt.subplots(figsize=size)
    for t, v in values_by_tool:
        if len(v):
            ax.hist(v, bins=BINS, weights=np.full(len(v), 100 / len(v)), histtype="step",
                    color=TOOL_COLOR[t], lw=1.4)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Composite FAIR score")
    ax.set_ylabel("Share of datasets, %")
    clean(ax)
    fig.tight_layout()
    save(fig, out, name)


def single_hist(v, tool, out, name):
    fig, ax = plt.subplots(figsize=(3.33, 1.6))
    if len(v):
        ax.hist(v, bins=BINS, weights=np.full(len(v), 100 / len(v)), color=TOOL_COLOR[tool], edgecolor="white", lw=0.4)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Composite FAIR score")
    ax.set_ylabel("Share of datasets, %")
    clean(ax)
    fig.tight_layout()
    save(fig, out, name)


def summarize(g, tools, principles, extra):
    rows = []
    for t in tools:
        for p in principles + ["F", "A", "I", "R", "composite"]:
            v = g.loc[g.tool == t, p].dropna()
            if v.empty:
                continue
            rows.append(dict(**extra, tool=t, score=p, n=len(v), distinct=v.round(6).nunique(),
                             mean=v.mean(), median=v.median(), sd=v.std(ddof=0),
                             share_0=(v.abs() < 1e-9).mean(), share_1=(v > 1 - 1e-9).mean()))
    return rows


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=os.path.join(here, "scores.csv"))
    ap.add_argument("--out", default=os.path.join(here, "results"))
    a = ap.parse_args()
    if not os.path.exists(a.csv):
        sys.exit(f"{a.csv} not found. Run merge.py first.")
    os.makedirs(a.out, exist_ok=True)
    dist_dir = os.path.join(a.out, "distributions")
    os.makedirs(dist_dir, exist_ok=True)
    df = pd.read_csv(a.csv)
    tools = [t for t in TOOLS if t in set(df.tool)]
    principles = [p for p in PRINCIPLES if p in df.columns]
    clouds = [c for c in ORDER if c in set(df.subcloud)] + sorted(set(df.subcloud) - set(ORDER))
    u = unique_assessments(df)
    lines = [f"RQ1 uses {u['dataset_id'].nunique()} unique datasets; RQ3 uses {len(df) // len(tools)} assessments"]

    means = u.groupby("tool")[principles].mean().reindex(tools)
    means.round(3).to_csv(os.path.join(a.out, "rq1_principle_means.csv"))
    fig, ax = plt.subplots(figsize=(3.33, 1.25))
    im = heat(ax, means.values, tools, principles)
    ax.xaxis.tick_top()
    plt.setp(ax.get_xticklabels(), rotation=45, ha="left", rotation_mode="anchor")
    fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02).outline.set_linewidth(0.4)
    save(fig, a.out, "fig_rq1_principle_means")

    summ = pd.DataFrame(summarize(u, tools, principles, {}))
    summ.round(3).to_csv(os.path.join(a.out, "rq1_distribution_summary.csv"), index=False)
    for t in tools:
        r = summ[(summ.tool == t) & (summ.score == "composite")].iloc[0]
        lines.append(f"{t}: {int(r.distinct)} distinct composite scores, median {r['median']:.2f}, "
                     f"{r.share_0:.0%} at 0, {r.share_1:.0%} at 1")

    grouped_principle_boxes(u, tools, principles, a.out, "fig_rq1_principle_distributions")
    for t in tools:
        single_principle_boxes(u, t, principles, a.out, f"fig_rq1_principle_distributions_{slug(t)}")

    overlay_hist([(t, u.loc[u.tool == t, "composite"].dropna()) for t in tools], a.out,
                 "fig_rq1_composite_distribution")
    for t in tools:
        single_hist(u.loc[u.tool == t, "composite"].dropna(), t, a.out, f"fig_rq1_composite_distribution_{slug(t)}")

    sm = df.pivot_table(index="subcloud", columns="tool", values="composite", aggfunc="mean").reindex(index=clouds, columns=tools)
    sm.round(3).to_csv(os.path.join(a.out, "rq3_subcloud_means.csv"))
    sm.rank(ascending=False, method="min").astype("Int64").to_csv(os.path.join(a.out, "rq3_subcloud_ranks.csv"))
    rho = sm.corr(method="spearman")
    rho.round(3).to_csv(os.path.join(a.out, "rq3_subcloud_rank_agreement.csv"))
    for i, t1 in enumerate(tools):
        for t2 in tools[i + 1:]:
            lines.append(f"RQ3 sub-cloud ranking agreement {t1} vs {t2}: Spearman {rho.loc[t1, t2]:+.2f}")

    fig, ax = plt.subplots(figsize=(3.33, 3.0))
    im = heat(ax, sm.values, clouds, tools)
    ax.xaxis.tick_top()
    fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(0.4)
    save(fig, a.out, "fig_rq3_subcloud_means")

    rk = sm.rank(ascending=False, method="first")
    fig, ax = plt.subplots(figsize=(3.33, 2.6))
    x = np.arange(len(tools))
    for c in clouds:
        d = rk.loc[c].values[-1] - rk.loc[c].values[0]
        col = UP if d < 0 else DOWN if d > 0 else MUTED
        ax.plot(x, rk.loc[c].values, color=col, lw=1.2, marker="o", ms=3.5, mfc=col, mec="white", mew=0.5,
                zorder=3 if col != MUTED else 2)
    n = len(clouds)
    left, right = rk[tools[0]].sort_values(), rk[tools[-1]].sort_values()
    ax.set_yticks(left.values, left.index)
    ax.set_ylim(n + 0.5, 0.5)
    for c, r in right.items():
        ax.text(x[-1] + 0.12, r, c, va="center", ha="left", fontsize=7, color=INK)
    ax.set_xticks(x, tools)
    ax.set_xlim(-0.15, len(tools) - 0.85)
    ax.tick_params(length=0)
    for s_ in ["top", "right"]:
        ax.spines[s_].set_visible(False)
    fig.tight_layout()
    save(fig, a.out, "fig_rq3_subcloud_ranks")

    rows = []
    for c in clouds:
        g = df[df.subcloud == c]
        rows += summarize(g, tools, principles, {"subcloud": c})
        grouped_principle_boxes(g, tools, principles, dist_dir, f"fig_rq1_principles_{slug(c)}")
        overlay_hist([(t, g.loc[g.tool == t, "composite"].dropna()) for t in tools], dist_dir,
                     f"fig_rq1_composite_{slug(c)}")
        for t in tools:
            single_principle_boxes(g, t, principles, dist_dir, f"fig_rq1_principles_{slug(c)}_{slug(t)}")
            single_hist(g.loc[g.tool == t, "composite"].dropna(), t, dist_dir, f"fig_rq1_composite_{slug(c)}_{slug(t)}")
    bysc = pd.DataFrame(rows)
    bysc.round(4).to_csv(os.path.join(a.out, "rq1_distribution_by_subcloud.csv"), index=False)
    for _, r in bysc[(bysc.score == "composite") & (bysc.distinct == 1)].iterrows():
        lines.append(f"{r.tool} gives every dataset in {r.subcloud} the same composite score ({r['mean']:.2f})")

    open(os.path.join(a.out, "rq_summary.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
