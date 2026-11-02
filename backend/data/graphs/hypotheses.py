import argparse
import itertools
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from scipy.stats import spearmanr, kendalltau, mannwhitneyu, rankdata

plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans",
                     "axes.linewidth": 0.5, "pdf.fonttype": 42})
TOOLS = ["FAIR-Checker", "F-UJI", "KGHeartBeat"]
SHORT = {"FAIR-Checker": "FC", "F-UJI": "FU", "KGHeartBeat": "KG"}
PAIRS = list(itertools.combinations(TOOLS, 2))
PAIR_NAME = {p: f"{SHORT[p[0]]} vs {SHORT[p[1]]}" for p in PAIRS}
TOOL_COLOR = {"FAIR-Checker": "#2a78d6", "F-UJI": "#eb6834", "KGHeartBeat": "#1baf7a"}
PAIR_COLOR = {PAIRS[0]: "#6250d6", PAIRS[1]: "#e87ba4", PAIRS[2]: "#008300"}
SHARED = "#2a78d6"
DIVERGENT = "#eb6834"
PRINCIPLES = ["F1", "F2", "F3", "A1", "A1.2", "I1", "I2", "I3", "R1.1", "R1.2", "R1.3"]
ORDER = ["BLOD", "CHeCLOUD", "Cross-domain", "Geography", "Government", "Life Sciences",
         "Linguistic", "Media", "Publications", "Social Networking", "User Generated"]
SOURCE = {
    "F-UJI": {"F1": "identifier", "F2": "metadata", "F3": "metadata", "A1": "protocol", "A1.2": "protocol",
              "I1": "metadata", "I2": "metadata", "I3": "metadata", "R1.1": "metadata", "R1.2": "metadata",
              "R1.3": "metadata"},
    "FAIR-Checker": {"F1": "identifier", "F2": "metadata", "A1": "protocol", "A1.2": "protocol",
                     "I1": "metadata", "I2": "metadata", "I3": "metadata", "R1.1": "metadata",
                     "R1.2": "metadata", "R1.3": "metadata"},
    "KGHeartBeat": {"F1": "graph", "F2": "metadata", "F3": "metadata", "A1": "endpoint", "A1.2": "endpoint",
                    "I1": "graph", "I2": "graph", "I3": "graph", "R1.1": "metadata", "R1.2": "metadata",
                    "R1.3": "graph"},
}
FEATURES = {"pid_doi": "Share with a DOI",
            "metadata_completeness": "Mean metadata completeness", "interlinked": "Share linking to other datasets",
            "endpoint": "Mean endpoint or dump availability"}
EPS = 1e-9
RNG = np.random.default_rng(7)


def save(fig, out, name):
    fig.savefig(os.path.join(out, f"{name}.pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(out, f"{name}.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def clean(ax, grid="y"):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    if grid:
        ax.grid(axis=grid, color="0.9", lw=0.4)
        ax.set_axisbelow(True)


def rho(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    if len(x) < 4 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return np.nan
    return spearmanr(x, y)[0]


def tie_share(v):
    v = pd.Series(v).dropna().round(6)
    n = len(v)
    if n < 2:
        return np.nan
    c = v.value_counts().values
    return float((c * (c - 1)).sum() / (n * (n - 1)))


def order_first(df):
    df = df.copy()
    df["_o"] = df["subcloud"].map({s: i for i, s in enumerate(ORDER)}).fillna(99)
    return df


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=os.path.join(here, "scores.csv"))
    ap.add_argument("--features", default=os.path.join(here, "kg_features.csv"))
    ap.add_argument("--out", default=os.path.join(here, "results", "hypotheses"))
    a = ap.parse_args()
    if not os.path.exists(a.csv):
        sys.exit(f"{a.csv} not found. Run merge.py first.")
    os.makedirs(a.out, exist_ok=True)
    df = pd.read_csv(a.csv)
    principles = [p for p in PRINCIPLES if p in df.columns]
    clouds = [c for c in ORDER if c in set(df.subcloud)] + sorted(set(df.subcloud) - set(ORDER))
    lines = []

    cols = principles + ["F", "A", "I", "R", "composite"]
    wide = df.pivot_table(index=["dataset_id", "subcloud"], columns="tool", values=cols, aggfunc="first")
    wl = order_first(wide.reset_index())
    first = wl.sort_values("_o").drop_duplicates(("dataset_id", ""))
    first = first.set_index([("dataset_id", ""), ("subcloud", "")])

    rows = []
    for (t1, t2), p in itertools.product(PAIRS, principles):
        s1, s2 = SOURCE[t1].get(p), SOURCE[t2].get(p)
        if s1 is None or s2 is None:
            continue
        r = rho(first[(p, t1)], first[(p, t2)])
        rows.append(dict(pair=PAIR_NAME[(t1, t2)], principle=p, source_1=s1, source_2=s2,
                         relation="shared" if s1 == s2 else "divergent", rho=r))
    h1 = pd.DataFrame(rows)
    h1.round(4).to_csv(os.path.join(a.out, "h1_principle_agreement.csv"), index=False)
    sh = h1[(h1.relation == "shared")]["rho"].dropna()
    dv = h1[(h1.relation == "divergent")]["rho"].dropna()
    p_mw = mannwhitneyu(sh, dv, alternative="greater").pvalue if len(sh) > 1 and len(dv) > 1 else np.nan
    lines.append(f"H1 principle-level rho: shared-source mean {sh.mean():+.3f} (n={len(sh)}), "
                 f"divergent-source mean {dv.mean():+.3f} (n={len(dv)}), one-sided Mann-Whitney p={p_mw:.3g}; "
                 f"{h1.rho.isna().sum()} undefined")

    fig, ax = plt.subplots(figsize=(3.33, 2.3))
    for k, rel in enumerate(["shared", "divergent"]):
        g = h1[(h1.relation == rel)].dropna(subset=["rho"])
        jit = RNG.uniform(-0.18, 0.18, len(g))
        for pair, col in PAIR_COLOR.items():
            m = (g.pair == PAIR_NAME[pair]).values
            ax.scatter(k + jit[m], g.rho.values[m], s=16, c=col, lw=0.4, edgecolors="white", zorder=3)
        if len(g):
            ax.plot([k - 0.3, k + 0.3], [g.rho.mean()] * 2, color="#1a1a1a", lw=1.6, zorder=4)
    ax.axhline(0, color="0.75", lw=0.5)
    ax.set_xticks([0, 1], ["Shared source", "Divergent source"])
    ax.set_ylabel("Principle-level Spearman ρ")
    ax.set_xlabel("Information source of the two tools")
    ax.set_xlim(-0.6, 1.6)
    clean(ax)
    fig.tight_layout()
    save(fig, a.out, "fig_h1_shared_vs_divergent")

    M = h1.pivot(index="principle", columns="pair", values="rho").reindex(index=principles,
                                                                          columns=[PAIR_NAME[p] for p in PAIRS])
    R = h1.pivot(index="principle", columns="pair", values="relation").reindex(index=principles,
                                                                               columns=[PAIR_NAME[p] for p in PAIRS])
    fig, ax = plt.subplots(figsize=(3.0, 3.0))
    im = ax.imshow(np.ma.masked_invalid(M.values.astype(float)), cmap="RdBu_r",
                   norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1), aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if R.iat[i, j] == "divergent":
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="#1a1a1a", lw=1.2))
            if pd.isna(M.iat[i, j]):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, hatch="////", lw=0, ec="0.6"))
    ax.set_xticks(range(3), M.columns)
    ax.set_yticks(range(len(principles)), principles)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(0.4)
    save(fig, a.out, "fig_h1_principle_heatmap")

    u = order_first(df).sort_values("_o")
    keep = u.drop_duplicates(["dataset_id", "tool"])
    h2 = []
    for t in TOOLS:
        v = keep.loc[keep.tool == t, "composite"]
        h2.append(dict(tool=t, n=v.notna().sum(), distinct=v.round(6).nunique(), tie_share=tie_share(v)))
    h2 = pd.DataFrame(h2)
    for t1, t2 in PAIRS:
        r = rho(first[("composite", t1)], first[("composite", t2)])
        x, y = first[("composite", t1)].astype(float), first[("composite", t2)].astype(float)
        m = ~(x.isna() | y.isna())
        tau = kendalltau(x[m], y[m])[0] if m.sum() > 3 else np.nan
        lines.append(f"H2 {PAIR_NAME[(t1, t2)]}: Spearman {r:+.3f}, Kendall tau-b {tau:+.3f}, gap {r - tau:+.3f}")
    h2.round(4).to_csv(os.path.join(a.out, "h2_granularity.csv"), index=False)
    for _, r in h2.iterrows():
        lines.append(f"H2 {r.tool}: {int(r.distinct)} distinct composite values, {r.tie_share:.1%} of dataset pairs tied")

    for metric, ylab, name in [("distinct", "Distinct composite scores", "fig_h2_distinct_values"),
                               ("tie_share", "Share of tied dataset pairs", "fig_h2_tie_share")]:
        fig, ax = plt.subplots(figsize=(2.4, 1.9))
        ax.bar(range(len(h2)), h2[metric], color=[TOOL_COLOR[t] for t in h2.tool], width=0.6, lw=0)
        ax.set_xticks(range(len(h2)), h2.tool)
        ax.set_ylabel(ylab)
        if metric == "distinct":
            ax.set_yscale("log")
        clean(ax)
        fig.tight_layout()
        save(fig, a.out, name)

    sc_rows = []
    for c in clouds:
        g = wide.xs(c, level="subcloud")
        for t1, t2 in PAIRS:
            x, y = g[("composite", t1)].astype(float), g[("composite", t2)].astype(float)
            m = ~(x.isna() | y.isna())
            if m.sum() > 3 and np.ptp(x[m]) and np.ptp(y[m]):
                sc_rows.append(dict(subcloud=c, pair=PAIR_NAME[(t1, t2)], n=int(m.sum()),
                                    rho=spearmanr(x[m], y[m])[0], tau=kendalltau(x[m], y[m])[0]))
    sct = pd.DataFrame(sc_rows, columns=["subcloud", "pair", "n", "rho", "tau"])
    sct.round(4).to_csv(os.path.join(a.out, "h2_rho_vs_tau_by_subcloud.csv"), index=False)
    fig, ax = plt.subplots(figsize=(2.6, 2.6))
    for pair, col in PAIR_COLOR.items():
        g = sct[sct.pair == PAIR_NAME[pair]]
        if g.empty:
            continue
        ax.scatter(g.rho, g.tau, s=np.sqrt(g.n) * 1.5, c=col, lw=0.4, edgecolors="white", alpha=.85, zorder=3)
    ax.plot([-1, 1], [-1, 1], ls=":", c="0.6", lw=0.8)
    ax.set_xlim(-0.5, 1.02); ax.set_ylim(-0.5, 1.02); ax.set_aspect("equal")
    ax.set_xlabel("Spearman ρ"); ax.set_ylabel("Kendall τ-b")
    clean(ax, grid=None)
    fig.tight_layout()
    save(fig, a.out, "fig_h2_rho_vs_tau")

    shares = np.arange(0.05, 0.51, 0.05)
    tk = []
    for t1, t2 in PAIRS:
        x = first[("composite", t1)].astype(float).values
        y = first[("composite", t2)].astype(float).values
        m = ~(np.isnan(x) | np.isnan(y))
        x, y = x[m], y[m]
        n = len(x)
        for sh_ in shares:
            k = max(1, int(round(sh_ * n)))
            ov = []
            for _ in range(200):
                i1 = np.lexsort((RNG.random(n), -x))[:k]
                i2 = np.lexsort((RNG.random(n), -y))[:k]
                ov.append(len(np.intersect1d(i1, i2)) / k)
            tk.append(dict(pair=PAIR_NAME[(t1, t2)], share=sh_, mean=np.mean(ov),
                           lo=np.percentile(ov, 2.5), hi=np.percentile(ov, 97.5)))
    tkd = pd.DataFrame(tk)
    tkd.round(4).to_csv(os.path.join(a.out, "h2_topk_tiebreak.csv"), index=False)
    fig, ax = plt.subplots(figsize=(3.33, 2.2))
    for pair, col in PAIR_COLOR.items():
        g = tkd[tkd.pair == PAIR_NAME[pair]]
        ax.fill_between(g.share * 100, g.lo * 100, g.hi * 100, color=col, alpha=0.2, lw=0)
        ax.plot(g.share * 100, g["mean"] * 100, color=col, lw=1.6)
    ax.plot(shares * 100, shares * 100, ls=":", c="0.5", lw=0.9)
    ax.set_xlabel("Top share of datasets, %")
    ax.set_ylabel("Overlap of top sets, %")
    ax.set_ylim(0, 100)
    clean(ax)
    fig.tight_layout()
    save(fig, a.out, "fig_h2_topk_tiebreak")
    w10 = tkd[np.isclose(tkd.share, 0.10)]
    for _, r in w10.iterrows():
        lines.append(f"H2 top-10% overlap {r.pair}: {r['mean']:.1%} (tie-break range {r.lo:.1%}-{r.hi:.1%})")

    multi = df.groupby(["dataset_id", "tool"]).filter(lambda g: g["subcloud"].nunique() >= 2)
    multi = order_first(multi).sort_values(["dataset_id", "_o"])
    rr = []
    for t in TOOLS:
        g = multi[multi.tool == t]
        a1 = g.groupby("dataset_id").nth(0).set_index("dataset_id")
        a2 = g.groupby("dataset_id").nth(1).set_index("dataset_id")
        j = a1.join(a2, lsuffix="_1", rsuffix="_2", how="inner")
        if j.empty:
            continue
        same = j["url_1"].fillna("") == j["url_2"].fillna("")
        for path, m in [("Same URL", same), ("Different URL", ~same)]:
            d = (j.loc[m, "composite_1"] - j.loc[m, "composite_2"]).abs()
            for v in d:
                rr.append(dict(tool=t, path=path, abs_diff=v))
            if len(d):
                lines.append(f"H3 {t} [{path}]: n={len(d)}, identical={int((d < EPS).sum())}, "
                             f"mean |diff|={d.mean():.3f}, max |diff|={d.max():.2f}")
    rrd = pd.DataFrame(rr)
    rrd.to_csv(os.path.join(a.out, "h3_retest_differences.csv"), index=False)
    if not rrd.empty:
        fig, ax = plt.subplots(figsize=(3.33, 2.1))
        paths = ["Same URL", "Different URL"]
        for i, t in enumerate(TOOLS):
            for k, path in enumerate(paths):
                v = rrd[(rrd.tool == t) & (rrd.path == path)].abs_diff.values
                if not len(v):
                    continue
                pos = k * 4 + i
                bp = ax.boxplot([v], positions=[pos], widths=0.7, showfliers=False, patch_artist=True,
                                boxprops=dict(facecolor=TOOL_COLOR[t] + "55", edgecolor=TOOL_COLOR[t], lw=0.7),
                                medianprops=dict(color=TOOL_COLOR[t], lw=1.4),
                                whiskerprops=dict(color=TOOL_COLOR[t], lw=0.7), capprops=dict(color=TOOL_COLOR[t], lw=0.7))
                ax.scatter(pos + RNG.uniform(-0.2, 0.2, len(v)), v, s=4, c=TOOL_COLOR[t], alpha=0.5, lw=0, zorder=3)
        ax.set_xticks([1, 5], paths)
        ax.set_xlabel("Access path in the two runs")
        ax.set_ylabel("Absolute composite difference")
        clean(ax)
        fig.tight_layout()
        save(fig, a.out, "fig_h3_retest_by_access_path")

    feats = pd.read_csv(a.features) if os.path.exists(a.features) else None
    pct = df.copy()
    pct["pct"] = pct.groupby(["subcloud", "tool"])["composite"].rank(pct=True)
    pw = pct.pivot_table(index=["dataset_id", "subcloud"], columns="tool", values="pct", aggfunc="first")
    if feats is not None and "endpoint" in feats:
        pw = pw.join(feats.set_index(["dataset_id", "subcloud"]), how="left")
        pw["route"] = np.where(pw["endpoint"] >= 1 - EPS, "Endpoint or dump working", "No working endpoint")
        dis = []
        for t1, t2 in PAIRS:
            d = (pw[t1] - pw[t2]).abs()
            for route in ["Endpoint or dump working", "No working endpoint"]:
                v = d[pw.route == route].dropna()
                dis.append(dict(pair=PAIR_NAME[(t1, t2)], route=route, n=len(v), mean=v.mean(), median=v.median()))
            lines.append("H3 " + PAIR_NAME[(t1, t2)] + ": mean rank disagreement " + ", ".join(
                f"{r['route']} {r['mean']:.3f} (n={r['n']})" for r in dis[-2:]))
        pd.DataFrame(dis).round(4).to_csv(os.path.join(a.out, "h3_disagreement_by_route.csv"), index=False)
        fig, ax = plt.subplots(figsize=(3.33, 2.1))
        routes = ["Endpoint or dump working", "No working endpoint"]
        for i, (t1, t2) in enumerate(PAIRS):
            d = (pw[t1] - pw[t2]).abs()
            for k, route in enumerate(routes):
                v = d[pw.route == route].dropna().values
                if not len(v):
                    continue
                col = PAIR_COLOR[(t1, t2)]
                ax.boxplot([v], positions=[k * 4 + i], widths=0.7, showfliers=False, patch_artist=True,
                           boxprops=dict(facecolor=col + "55", edgecolor=col, lw=0.7),
                           medianprops=dict(color=col, lw=1.4), whiskerprops=dict(color=col, lw=0.7),
                           capprops=dict(color=col, lw=0.7))
        ax.set_xticks([1, 5], routes)
        ax.set_ylabel("Rank disagreement within sub-cloud")
        clean(ax)
        fig.tight_layout()
        save(fig, a.out, "fig_h3_disagreement_by_route")

        prev = feats.groupby("subcloud")[[f for f in FEATURES if f in feats]].mean().reindex(clouds)
        prev.round(4).to_csv(os.path.join(a.out, "h4_subcloud_features.csv"))
        agree = []
        for c in clouds:
            g = wide.xs(c, level="subcloud")
            for t1, t2 in PAIRS:
                agree.append(dict(subcloud=c, pair=PAIR_NAME[(t1, t2)], n=len(g),
                                  rho=rho(g[("composite", t1)], g[("composite", t2)])))
        ag = pd.DataFrame(agree)
        ag.round(4).to_csv(os.path.join(a.out, "h4_subcloud_agreement.csv"), index=False)
        h4 = []
        for f, lab in FEATURES.items():
            if f not in prev:
                continue
            if prev[f].nunique() < 2:
                lines.append(f"H4 {f}: identical in every sub-cloud, no correlation possible")
            fig, ax = plt.subplots(figsize=(2.6, 2.2))
            for pair, col in PAIR_COLOR.items():
                g = ag[ag.pair == PAIR_NAME[pair]].set_index("subcloud").join(prev[[f]])
                g = g.dropna(subset=["rho", f])
                if g.empty:
                    continue
                ax.scatter(g[f], g.rho, s=np.sqrt(g.n) * 1.6, c=col, lw=0.4, edgecolors="white", alpha=.85, zorder=3)
                if len(g) >= 4 and g[f].nunique() >= 2:
                    r_, p_ = spearmanr(g[f], g.rho)
                    h4.append(dict(feature=f, pair=PAIR_NAME[pair], n_subclouds=len(g), rho=r_, p=p_))
                    lines.append(f"H4 {f} vs agreement {PAIR_NAME[pair]}: Spearman {r_:+.2f} "
                                 f"(p={p_:.3g}, {len(g)} sub-clouds)")
            ax.axhline(0, color="0.75", lw=0.5)
            ax.set_xlabel(lab)
            ax.set_ylabel("Within-sub-cloud Spearman ρ")
            clean(ax, grid=None)
            fig.tight_layout()
            save(fig, a.out, f"fig_h4_{f}_vs_agreement")
        pd.DataFrame(h4).round(4).to_csv(os.path.join(a.out, "h4_feature_correlations.csv"), index=False)

        fig, ax = plt.subplots(figsize=(3.33, 2.9))
        Z = prev.values.astype(float)
        im = ax.imshow(Z, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
        short = {"pid_doi": "DOI", "metadata_completeness": "Metadata", "interlinked": "Interlinked", "endpoint": "Endpoint"}
        ax.set_xticks(range(len(FEATURES)), [short.get(f, f) for f in FEATURES],
                      rotation=45, ha="right", rotation_mode="anchor")
        ax.set_yticks(range(len(clouds)), clouds)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(0.4)
        fig.tight_layout()
        save(fig, a.out, "fig_h4_subcloud_features")
    else:
        lines.append("H3 route split and H4 skipped: kg_features.csv not found (rerun merge.py)")

    for t1, t2 in PAIRS:
        x = first[("composite", t1)].astype(float)
        y = first[("composite", t2)].astype(float)
        pooled = rho(x, y)
        sub = pd.Series([i[1] for i in first.index], index=first.index)
        rx = x.groupby(sub).rank(pct=True)
        ry = y.groupby(sub).rank(pct=True)
        lines.append(f"H4 {PAIR_NAME[(t1, t2)]}: pooled rho {pooled:+.3f}, stratified rho {rho(rx, ry):+.3f}")

    open(os.path.join(a.out, "hypotheses_summary.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
