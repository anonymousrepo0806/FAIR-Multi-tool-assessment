import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans",
                     "axes.linewidth": 0.5, "pdf.fonttype": 42})
TOOLS = ["FAIR-Checker", "F-UJI", "KGHeartBeat"]
PRINCIPLES = ["F1", "F2", "F3", "A1", "A1.2", "I1", "I2", "I3", "R1.1", "R1.2", "R1.3"]
ORDER = ["BLOD", "CHeCLOUD", "Cross-domain", "Geography", "Government", "Life Sciences",
         "Linguistic", "Media", "Publications", "Social Networking", "User Generated"]
INK = "#2b2b2b"
FAIL = "#b2182b"
PASS = "#2166ac"
EPS = 1e-9
DIM_COLOR = {"F": "#6250d6", "A": "#eda100", "I": "#008300", "R": "#e87ba4"}
BAR = "#3d4a5c"


def dim_color(p):
    return DIM_COLOR.get(p[0], INK)


def consensus(df, principles, rule):
    wide = df.pivot_table(index=["dataset_id", "subcloud"], columns="tool", values=principles, aggfunc="first")
    fail = pd.DataFrame(index=wide.index)
    ok = pd.DataFrame(index=wide.index)
    for p in principles:
        block = wide[p]
        impl = block.notna().sum(axis=1)
        zeros = (block.abs() < EPS).sum(axis=1)
        ones = (block > 1 - EPS).sum(axis=1)
        need = impl if rule == "all" else np.floor(impl / 2) + 1
        valid = impl >= 2
        fail[p] = valid & (zeros >= need)
        ok[p] = valid & (ones >= need)
    return fail, ok


def save(fig, out, name):
    fig.savefig(os.path.join(out, f"{name}.pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(out, f"{name}.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def upset(fail, principles, out, name, top):
    if fail.empty:
        return pd.DataFrame()
    pattern = fail[principles].apply(lambda r: tuple(p for p in principles if r[p]), axis=1)
    counts = pattern.value_counts()
    counts = counts[[len(k) > 0 for k in counts.index]]
    if counts.empty:
        return pd.DataFrame()
    shown = counts.iloc[:top]
    rest = int(counts.iloc[top:].sum())
    labels = [k for k in shown.index]
    sizes = list(shown.values) + ([rest] if rest else [])
    ncol = len(sizes)
    rows = [p for p in principles if fail[p].any()]
    set_sizes = fail[rows].sum()

    fig = plt.figure(figsize=(max(3.33, 0.28 * ncol + 1.6), 0.18 * len(rows) + 1.6))
    gs = GridSpec(2, 2, width_ratios=[1, max(3, ncol * 0.35)], height_ratios=[1.2, 0.16 * len(rows) + 0.2],
                  wspace=0.32, hspace=0.05, figure=fig)
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_mat = fig.add_subplot(gs[1, 1], sharex=ax_bar)
    ax_set = fig.add_subplot(gs[1, 0], sharey=ax_mat)
    x = np.arange(ncol)
    ax_bar.bar(x, sizes, width=0.6, color=BAR, lw=0)
    ax_bar.set_ylabel("Datasets")
    for s in ["top", "right", "bottom"]:
        ax_bar.spines[s].set_visible(False)
    ax_bar.tick_params(axis="x", length=0, labelbottom=False)
    ax_bar.grid(axis="y", color="0.9", lw=0.4)
    ax_bar.set_axisbelow(True)

    y = {p: i for i, p in enumerate(rows)}
    for j in range(ncol):
        ax_mat.scatter([j] * len(rows), range(len(rows)), s=14, c="0.88", lw=0, zorder=1)
    for j, combo in enumerate(labels):
        ys = sorted(y[p] for p in combo if p in y)
        if len(ys) > 1:
            ax_mat.plot([j, j], [ys[0], ys[-1]], color=BAR, lw=1.2, zorder=2)
        ax_mat.scatter([j] * len(ys), ys, s=18, c=[dim_color(rows[k]) for k in ys], lw=0.4, edgecolors="white", zorder=3)
    ax_mat.set_yticks(range(len(rows)), rows)
    ax_mat.set_ylim(len(rows) - 0.5, -0.5)
    xt = [""] * len(labels) + (["Other"] if rest else [])
    ax_mat.set_xticks(x, xt)
    ax_mat.set_xlim(-0.6, ncol - 0.4)
    ax_mat.tick_params(length=0)
    for s in ax_mat.spines.values():
        s.set_visible(False)

    ax_set.barh(range(len(rows)), set_sizes.values, height=0.6, color=[dim_color(p) for p in rows], lw=0)
    ax_set.invert_xaxis()
    ax_set.set_xlabel("Datasets failing")
    ax_set.tick_params(axis="y", length=0, labelleft=False)
    for s in ["top", "left", "right"]:
        ax_set.spines[s].set_visible(False)
    save(fig, out, name)
    return pd.DataFrame({"principles_failed": ["+".join(k) for k in counts.index], "datasets": counts.values})


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=os.path.join(here, "scores.csv"))
    ap.add_argument("--out", default=os.path.join(here, "results"))
    ap.add_argument("--rule", choices=["all", "majority"], default="all")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    if not os.path.exists(a.csv):
        sys.exit(f"{a.csv} not found. Run merge.py first.")
    os.makedirs(a.out, exist_ok=True)
    up_dir = os.path.join(a.out, "upset")
    os.makedirs(up_dir, exist_ok=True)
    df = pd.read_csv(a.csv)
    principles = [p for p in PRINCIPLES if p in df.columns]
    fail, ok = consensus(df, principles, a.rule)
    clouds = [c for c in ORDER if c in set(df.subcloud)] + sorted(set(df.subcloud) - set(ORDER))
    lines = [f"Consensus rule: {a.rule} tools implementing a principle score 0 for failure, 1 for pass; "
             f"principles implemented by fewer than 2 tools are skipped"]

    impl = df.groupby("tool")[principles].apply(lambda g: g.notna().any())
    lines.append("Tools implementing each principle: " + ", ".join(
        f"{p}={int(impl[p].sum())}" for p in principles))
    if "F-UJI" in impl.index and "A1.2" in principles:
        fu = df.loc[df.tool == "F-UJI", "A1.2"].dropna()
        lines.append(f"F-UJI A1.2 check: {(fu > 1 - EPS).mean():.1%} of assessments at full marks, "
                     f"{(fu.abs() < EPS).mean():.1%} at 0")

    rows = []
    for c in clouds:
        f = fail.xs(c, level="subcloud")
        o = ok.xs(c, level="subcloud")
        for p in principles:
            rows.append(dict(subcloud=c, principle=p, n=len(f),
                             consensus_fail=f[p].mean(), consensus_pass=o[p].mean(),
                             no_consensus=1 - f[p].mean() - o[p].mean()))
    by_p = pd.DataFrame(rows)
    by_p.round(4).to_csv(os.path.join(a.out, "consensus_by_principle.csv"), index=False)

    nfail = fail.sum(axis=1)
    kmax = len(principles)
    ks = list(range(1, kmax + 1))
    atk = pd.DataFrame({k: nfail.groupby(level="subcloud").apply(lambda s: (s >= k).mean()) for k in ks}).reindex(clouds)
    atk.round(4).to_csv(os.path.join(a.out, "consensus_failure_at_least_k.csv"))

    fig, ax = plt.subplots(figsize=(3.33, 2.9))
    im = ax.imshow(atk.values, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(ks)), ks)
    ax.set_yticks(range(len(clouds)), clouds)
    ax.set_xlabel("Minimum number of principles with consensus failure")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(0.4)
    save(fig, a.out, "fig_consensus_failure_at_least_k")

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
    for ax, col, cmap, lab in [(axes[0], "consensus_fail", "Reds", "Consensus failure share"),
                               (axes[1], "consensus_pass", "Blues", "Consensus pass share")]:
        M = by_p.pivot(index="subcloud", columns="principle", values=col).reindex(index=clouds, columns=principles)
        im = ax.imshow(M.values, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(principles)), principles, rotation=45, ha="right", rotation_mode="anchor")
        ax.set_xlabel(lab)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02).outline.set_linewidth(0.4)
    axes[0].set_yticks(range(len(clouds)), clouds)
    fig.tight_layout()
    save(fig, a.out, "fig_consensus_fail_vs_pass")
    single = os.path.join(a.out, "single")
    os.makedirs(single, exist_ok=True)
    for col, cmap, lab, nm in [("consensus_fail", "Reds", "Consensus failure share", "fail"),
                               ("consensus_pass", "Blues", "Consensus pass share", "pass")]:
        M = by_p.pivot(index="subcloud", columns="principle", values=col).reindex(index=clouds, columns=principles)
        fig, ax = plt.subplots(figsize=(3.5, 2.9))
        im = ax.imshow(M.values, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(principles)), principles, rotation=45, ha="right", rotation_mode="anchor")
        ax.set_yticks(range(len(clouds)), clouds)
        ax.set_xlabel(lab)
        ax.tick_params(length=0)
        for s_ in ax.spines.values():
            s_.set_visible(False)
        fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(0.4)
        fig.tight_layout()
        save(fig, single, f"fig_consensus_{nm}_by_subcloud")

    first = fail.reset_index()
    first["_o"] = first["subcloud"].map({s: i for i, s in enumerate(ORDER)}).fillna(99)
    keep = first.sort_values("_o").drop_duplicates("dataset_id").set_index(["dataset_id", "subcloud"]).index
    fu, ou = fail.loc[keep], ok.loc[keep]
    fs, ps = fu.mean().reindex(principles), ou.mean().reindex(principles)
    fig, ax = plt.subplots(figsize=(3.33, 2.4))
    yy = np.arange(len(principles))
    ax.barh(yy, -fs.values, height=0.6, color=FAIL, lw=0)
    ax.barh(yy, ps.values, height=0.6, color=PASS, lw=0)
    ax.axvline(0, color=INK, lw=0.6)
    ax.set_yticks(yy, principles)
    ax.set_ylim(len(principles) - 0.5, -0.5)
    lim = max(0.05, float(np.nanmax(np.r_[fs.values, ps.values]))) * 1.05
    ax.set_xlim(-lim, lim)
    ticks = np.linspace(-lim, lim, 5)
    ax.set_xticks(ticks, [f"{abs(t):.0%}" for t in ticks])
    ax.set_xlabel("Consensus failure    |    Consensus pass")
    ax.tick_params(axis="y", length=0)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="0.9", lw=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, a.out, "fig_consensus_fail_pass_by_principle")

    for c in clouds:
        f = fail.xs(c, level="subcloud")
        tab = upset(f, principles, up_dir, f"fig_upset_{c.replace(' ', '_')}", a.top)
        if not tab.empty:
            tab.to_csv(os.path.join(up_dir, f"upset_{c.replace(' ', '_')}.csv"), index=False)
            if c == "BLOD":
                upset(f, principles, a.out, "fig_upset_BLOD", a.top)
            top_share = tab["datasets"].iloc[0] / len(f)
            lines.append(f"{c}: largest consensus-failure pattern covers {tab['datasets'].iloc[0]} of {len(f)} "
                         f"datasets ({top_share:.0%}), failing {tab['principles_failed'].iloc[0]}")
    for c in clouds:
        r = atk.loc[c]
        lines.append(f"{c}: share with consensus failure on at least 1 / 3 / 6 principles = "
                     f"{r[1]:.0%} / {r.get(3, np.nan):.0%} / {r.get(6, np.nan):.0%}")

    open(os.path.join(a.out, "consensus_summary.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
