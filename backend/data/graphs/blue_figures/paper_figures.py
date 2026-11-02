import os
import sys
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#222222",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": "#DDDDDD",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "savefig.dpi": 300,
})

TOOLS = ["FAIR-Checker", "F-UJI", "KGHeartBeat"]
SHORT = {"FAIR-Checker": "FC", "F-UJI": "FU", "KGHeartBeat": "KG"}
LIGHT_BLUE, MID_BLUE, DARK_BLUE = "#9ECAE1", "#4292C6", "#08519C"
TOOL_COLOR = {"FAIR-Checker": LIGHT_BLUE, "F-UJI": MID_BLUE, "KGHeartBeat": DARK_BLUE}
PAIRS = ["FC-FU", "FC-KG", "FU-KG"]
PAIR_LABEL = {"FC-FU": "FC vs FU", "FC-KG": "FC vs KG", "FU-KG": "FU vs KG"}
PAIR_COLOR = {"FC-FU": LIGHT_BLUE, "FC-KG": MID_BLUE, "FU-KG": DARK_BLUE}
PAIR_STYLE = {"FC-FU": ("o", "-"), "FC-KG": ("s", "--"), "FU-KG": ("^", "-.")}
FAIL, PASS = DARK_BLUE, LIGHT_BLUE
EDGE = "#222222"
BAR_EDGE = "#08306B"
DIMS = ["F", "A", "I", "R", "composite"]
DIM_LABEL = {"F": "Findability", "A": "Accessibility", "I": "Interoperability", "R": "Reusability", "composite": "Composite"}
PRINCIPLES = ["F1", "F2", "F3", "A1", "A1.2", "I1", "I2", "I3", "R1.1", "R1.2", "R1.3"]
ORDER = ["BLOD", "CHeCLOUD", "Cross-domain", "Geography", "Government", "Life Sciences",
         "Linguistic", "Media", "Publications", "Social Networking", "User Generated"]
EPS = 1e-9


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"{name}.pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(out, f"{name}.png"), bbox_inches="tight")
    plt.close(fig)


def need(path):
    if not os.path.exists(path):
        sys.exit(f"{path} not found. Run main.py first.")
    return pd.read_csv(path)


def grouped_bars(ax, groups, series, values, colors, errs=None, horizontal=False, width=0.8):
    n = len(series)
    w = width / n
    pos = np.arange(len(groups))
    for i, s in enumerate(series):
        off = (i - (n - 1) / 2) * w
        v = np.array([values[s].get(g, np.nan) for g in groups], float)
        e = None
        if errs is not None:
            lo = np.array([errs[s][0].get(g, np.nan) for g in groups], float)
            hi = np.array([errs[s][1].get(g, np.nan) for g in groups], float)
            e = np.vstack([np.clip(v - lo, 0, None), np.clip(hi - v, 0, None)])
            e = np.nan_to_num(e)
        kw = dict(color=colors[s], edgecolor=BAR_EDGE, linewidth=0.5)
        ekw = dict(elinewidth=0.6, capsize=1.5, ecolor=EDGE)
        ok = np.isfinite(v)
        if e is not None:
            e = e[:, ok]
        if horizontal:
            ax.barh((pos + off)[ok], v[ok], height=w, xerr=e, error_kw=ekw, **kw)
        else:
            ax.bar((pos + off)[ok], v[ok], width=w, yerr=e, error_kw=ekw, **kw)
    return pos


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    res = os.path.join(here, "results")
    out = os.path.join(here, "figures")
    os.makedirs(out, exist_ok=True)

    agr = need(os.path.join(res, "agreement_all.csv"))

    po = agr[agr.level == "pooled"]
    vals = {p: dict(zip(po[po.pair == p].dim, po[po.pair == p].rho)) for p in PAIRS}
    errs = {p: (dict(zip(po[po.pair == p].dim, po[po.pair == p].lo)),
                dict(zip(po[po.pair == p].dim, po[po.pair == p].hi))) for p in PAIRS}
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    pos = grouped_bars(ax, DIMS, PAIRS, vals, PAIR_COLOR, errs)
    ax.axhline(0, color=EDGE, lw=0.8)
    ax.set_xticks(pos, [DIM_LABEL[d] for d in DIMS], rotation=20, ha="right", rotation_mode="anchor")
    ax.set_ylabel("Spearman $\\rho$")
    ax.set_xlabel("FAIR dimension")
    ax.set_ylim(-0.4, 1.0)
    save(fig, out, "fig1_agreement_by_dimension")

    sc = agr[(agr.level == "sub-cloud") & (agr.dim == "composite")]
    clouds = [c for c in ORDER if c in set(sc.group)] + sorted(set(sc.group) - set(ORDER))
    vals = {p: dict(zip(sc[sc.pair == p].group, sc[sc.pair == p].rho)) for p in PAIRS}
    errs = {p: (dict(zip(sc[sc.pair == p].group, sc[sc.pair == p].lo)),
                dict(zip(sc[sc.pair == p].group, sc[sc.pair == p].hi))) for p in PAIRS}
    fig, ax = plt.subplots(figsize=(3.4, 4.0))
    pos = grouped_bars(ax, clouds, PAIRS, vals, PAIR_COLOR, errs, horizontal=True)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.axvline(0, color=EDGE, lw=0.8)
    ax.set_yticks(pos, clouds)
    ax.set_ylim(len(clouds) - 0.5, -0.5)
    ax.set_xlim(-0.5, 1.05)
    ax.set_xlabel("Spearman $\\rho$ on composite scores")
    ax.set_ylabel("Sub-cloud")
    save(fig, out, "fig2_agreement_by_subcloud")

    st = need(os.path.join(res, "pooled_vs_stratified.csv"))
    st = st[st.dim == "composite"].set_index("pair")
    fig, ax = plt.subplots(figsize=(3.0, 2.0))
    pos = np.arange(len(PAIRS))
    w = 0.35
    for i, p in enumerate(PAIRS):
        ax.bar(pos[i] - w / 2, st.loc[p, "pooled"], width=w, color="white", hatch="////",
               edgecolor=PAIR_COLOR[p] if p != "FC-FU" else MID_BLUE, linewidth=0.8)
        ax.bar(pos[i] + w / 2, st.loc[p, "stratified"], width=w, color=PAIR_COLOR[p],
               edgecolor=BAR_EDGE, linewidth=0.5)
    ax.axhline(0, color=EDGE, lw=0.8)
    ax.set_xticks(pos, [PAIR_LABEL[p] for p in PAIRS])
    ax.set_ylabel("Spearman $\\rho$ on composite scores")
    ax.set_xlabel("Tool pair")
    ax.set_ylim(min(0, np.nanmin(st[["pooled", "stratified"]].values) - 0.05), 1.0)
    save(fig, out, "fig3_pooled_vs_within_subcloud")

    means = need(os.path.join(res, "rq1_principle_means.csv")).set_index("tool")
    prin = [p for p in PRINCIPLES if p in means.columns]
    vals = {t: means.loc[t, prin].to_dict() for t in TOOLS if t in means.index}
    fig, ax = plt.subplots(figsize=(7.0, 2.0))
    pos = grouped_bars(ax, prin, list(vals), vals, TOOL_COLOR)
    ax.set_xticks(pos, prin)
    ax.set_ylabel("Mean normalized score")
    ax.set_xlabel("FAIR principle")
    ax.set_ylim(0, 1.0)
    save(fig, out, "fig4_mean_score_by_principle")

    gran = need(os.path.join(res, "hypotheses", "h2_granularity.csv")).set_index("tool")
    fig, ax = plt.subplots(figsize=(2.6, 2.0))
    tl = [t for t in TOOLS if t in gran.index]
    ax.bar(range(len(tl)), gran.loc[tl, "tie_share"] * 100, width=0.6,
           color=[TOOL_COLOR[t] for t in tl], edgecolor=BAR_EDGE, linewidth=0.5)
    ax.set_xticks(range(len(tl)), tl)
    ax.set_ylabel("Tied dataset pairs, %")
    ax.set_xlabel("Tool")
    save(fig, out, "fig5_tied_pairs")

    tr = need(os.path.join(res, "test_retest.csv"))
    inv = {v: k for k, v in SHORT.items()}
    tr["tool"] = tr["tool"].map(lambda x: inv.get(x, x))
    paths = ["same URL", "different URL"]
    vals = {t: dict(zip(tr[tr.tool == t].subset, tr[tr.tool == t].mean_abs_diff)) for t in TOOLS if t in set(tr.tool)}
    fig, ax = plt.subplots(figsize=(3.0, 2.0))
    pos = grouped_bars(ax, paths, list(vals), vals, TOOL_COLOR, width=0.7)
    ax.set_xticks(pos, ["Same URL", "Different URL"])
    ax.set_ylabel("Mean absolute score change")
    ax.set_xlabel("Access path in the two assessments")
    save(fig, out, "fig6_rescoring_by_access_path")

    tk = need(os.path.join(res, "hypotheses", "h2_topk_tiebreak.csv"))
    tk["pair"] = tk["pair"].str.replace(" vs ", "-")
    fig, ax = plt.subplots(figsize=(3.2, 2.2))
    for p in PAIRS:
        g = tk[tk.pair == p]
        if g.empty:
            continue
        m, ls = PAIR_STYLE[p]
        ax.plot(g.share * 100, g["mean"] * 100, color=PAIR_COLOR[p],
                marker=m, ms=4.5, ls=ls, lw=1.6, mec=BAR_EDGE, mew=0.6)
    s = np.sort(tk.share.unique())
    ax.plot(s * 100, s * 100, color="#999999", ls=":", lw=1.0)
    ax.set_xlabel("Top share of datasets, %")
    ax.set_ylabel("Overlap of top sets, %")
    ax.set_ylim(0, 100)
    ax.set_xlim(0, s.max() * 100 + 2)
    save(fig, out, "fig7_top_k_overlap")

    df = need(os.path.join(here, "scores.csv"))
    prin = [p for p in PRINCIPLES if p in df.columns]
    df["_o"] = df["subcloud"].map({c: i for i, c in enumerate(ORDER)}).fillna(99)
    first = df.sort_values("_o").drop_duplicates("dataset_id")[["dataset_id", "subcloud"]]
    u = df.merge(first, on=["dataset_id", "subcloud"])
    wide = u.pivot_table(index="dataset_id", columns="tool", values=prin, aggfunc="first")
    fail, ok = {}, {}
    for p in prin:
        b = wide[p]
        impl = b.notna().sum(axis=1)
        valid = impl >= 2
        fail[p] = (valid & ((b.abs() < EPS).sum(axis=1) == impl)).mean() * 100
        ok[p] = (valid & ((b > 1 - EPS).sum(axis=1) == impl)).mean() * 100
    fig, ax = plt.subplots(figsize=(3.2, 2.6))
    y = np.arange(len(prin))
    ax.barh(y, [-fail[p] for p in prin], height=0.65, color=FAIL, edgecolor=BAR_EDGE, linewidth=0.5)
    ax.barh(y, [ok[p] for p in prin], height=0.65, color=PASS, edgecolor=BAR_EDGE, linewidth=0.5)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.axvline(0, color=EDGE, lw=0.8)
    ax.set_yticks(y, prin)
    ax.set_ylim(len(prin) - 0.5, -0.5)
    lim = max(5, max(max(fail.values()), max(ok.values()))) * 1.08
    ticks = np.linspace(-np.floor(lim / 20) * 20, np.floor(lim / 20) * 20, int(2 * np.floor(lim / 20)) + 1)
    ax.set_xlim(-lim, lim)
    ax.set_xticks(ticks, [f"{abs(t):.0f}" for t in ticks])
    ax.set_xlabel("Datasets, %:  all tools fail  |  all tools pass")
    ax.set_ylabel("FAIR principle")
    save(fig, out, "fig8_consensus_fail_pass")
    pd.DataFrame({"principle": prin, "consensus_fail_pct": [fail[p] for p in prin],
                  "consensus_pass_pct": [ok[p] for p in prin]}).round(2).to_csv(
        os.path.join(out, "fig8_consensus_fail_pass.csv"), index=False)

    sm = need(os.path.join(res, "rq3_subcloud_means.csv")).set_index("subcloud")
    clouds = [c for c in ORDER if c in sm.index] + sorted(set(sm.index) - set(ORDER))
    vals = {t: sm[t].to_dict() for t in TOOLS if t in sm.columns}
    fig, ax = plt.subplots(figsize=(3.4, 4.0))
    pos = grouped_bars(ax, clouds, list(vals), vals, TOOL_COLOR, horizontal=True)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_yticks(pos, clouds)
    ax.set_ylim(len(clouds) - 0.5, -0.5)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Mean composite FAIR score")
    ax.set_ylabel("Sub-cloud")
    save(fig, out, "fig9_mean_score_by_subcloud")

    print(f"9 paper figures written to {out}")


if __name__ == "__main__":
    main()
