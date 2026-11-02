import argparse, itertools, os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from scipy.stats import spearmanr, kendalltau, rankdata

from style import PAIR_COLOR, TOOL_COLOR, DIVERGING, MUTED, apply, light

apply()
ALIAS = {"fair-checker": "FC", "fairchecker": "FC", "fc": "FC",
         "f-uji": "FU", "fuji": "FU", "fu": "FU",
         "kgheartbeat": "KG", "kg": "KG"}
TOOLS = ["FC", "FU", "KG"]
PAIRS = list(itertools.combinations(TOOLS, 2))
DIMS = ["F", "A", "I", "R", "composite"]
DIM_LABEL = {"F": "F", "A": "A", "I": "I", "R": "R", "composite": "FAIR"}
ORDER = ["BLOD", "CHeCLOUD", "Cross-domain", "Geography", "Government", "Life Sciences",
         "Linguistic", "Media", "Publications", "Social Networking", "User Generated"]
B = 2000
RNG = np.random.default_rng(42)


def load(path):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    need = {"dataset_id", "subcloud", "tool", "F", "A", "I", "R"}
    miss = need - set(df.columns)
    if miss:
        sys.exit(f"missing columns: {sorted(miss)}")
    df["tool"] = df["tool"].str.strip().str.lower().map(ALIAS)
    if df["tool"].isna().any():
        sys.exit("unrecognised tool names; use FAIR-Checker / F-UJI / KGHeartBeat")
    if "composite" not in df:
        df["composite"] = df[["F", "A", "I", "R"]].mean(axis=1)
    return df


def wide(df, cols=DIMS):
    w = df.pivot_table(index=["dataset_id", "subcloud"], columns="tool", values=cols, aggfunc="first")
    w.columns = [f"{d}|{t}" for d, t in w.columns]
    return w.dropna()


def rho_ci(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 4 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return dict(n=n, rho=np.nan, lo=np.nan, hi=np.nan, p=np.nan, tau=np.nan)
    r, p = spearmanr(x, y)
    tau, _ = kendalltau(x, y)
    idx = RNG.integers(0, n, (B, n))
    rx = rankdata(x[idx], axis=1)
    ry = rankdata(y[idx], axis=1)
    rx -= rx.mean(axis=1, keepdims=True)
    ry -= ry.mean(axis=1, keepdims=True)
    den = np.sqrt((rx * rx).sum(axis=1) * (ry * ry).sum(axis=1))
    ok = den > 0
    bs = (rx * ry).sum(axis=1)[ok] / den[ok]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(n=n, rho=r, lo=lo, hi=hi, p=p, tau=tau)


def bh(p):
    p = np.asarray(p, float); ok = ~np.isnan(p); q = np.full_like(p, np.nan)
    ps = p[ok]; m = len(ps); o = np.argsort(ps)
    adj = np.minimum.accumulate((ps[o] * m / np.arange(1, m + 1))[::-1])[::-1]
    out = np.empty(m); out[o] = np.minimum(adj, 1); q[ok] = out
    return q


def holm(p):
    p = np.asarray(p, float); ok = ~np.isnan(p); q = np.full_like(p, np.nan)
    ps = p[ok]; m = len(ps); o = np.argsort(ps)
    adj = np.maximum.accumulate(ps[o] * (m - np.arange(m)))
    out = np.empty(m); out[o] = np.minimum(adj, 1); q[ok] = out
    return q


def by(p):
    p = np.asarray(p, float); ok = ~np.isnan(p)
    m = int(ok.sum())
    c = np.sum(1.0 / np.arange(1, m + 1)) if m else 1.0
    return np.minimum(bh(p) * c, 1)


def pooled_unique(w):
    w = w.reset_index()
    w["_o"] = w["subcloud"].map({s: i for i, s in enumerate(ORDER)}).fillna(99)
    return w.sort_values("_o").drop_duplicates("dataset_id", keep="first")


def heat(ax, M, rows, cols, title):
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    im = ax.imshow(np.ma.masked_invalid(M), cmap=DIVERGING, norm=norm, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            if np.isnan(v):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, hatch="////", lw=0, ec="0.65"))
    ax.set_xticks(range(len(cols)), cols); ax.xaxis.tick_top()
    ax.set_yticks(range(len(rows)), rows); ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    return im


def main():
    ap = argparse.ArgumentParser(); here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("csv", nargs="?", default=os.path.join(here, "scores.csv")); ap.add_argument("--out", default=os.path.join(here, "results"))
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    df = load(a.csv); w = wide(df)
    clouds = [c for c in ORDER if c in w.index.get_level_values("subcloud")] + \
             sorted(set(w.index.get_level_values("subcloud")) - set(ORDER))
    lines = []

    rows = []
    print("1/5 agreement per sub-cloud and dimension", flush=True)
    for (t1, t2), d, c in itertools.product(PAIRS, DIMS, clouds):
        sub = w.xs(c, level="subcloud")
        rows.append(dict(level="sub-cloud", group=c, pair=f"{t1}-{t2}", dim=d,
                         **rho_ci(sub[f"{d}|{t1}"], sub[f"{d}|{t2}"])))
    pu = pooled_unique(w)
    for (t1, t2), d in itertools.product(PAIRS, DIMS):
        rows.append(dict(level="pooled", group="all", pair=f"{t1}-{t2}", dim=d,
                         **rho_ci(pu[f"{d}|{t1}"], pu[f"{d}|{t2}"])))
    res = pd.DataFrame(rows); res["q_BH"] = bh(res["p"]); res["sig"] = res["q_BH"] < 0.05
    res["p_Holm"] = holm(res["p"]); res["sig_Holm"] = res["p_Holm"] < 0.05
    res["q_BY"] = by(res["p"]); res["sig_BY"] = res["q_BY"] < 0.05
    res.to_csv(f"{a.out}/agreement_all.csv", index=False)
    lines.append(f"Correlations tested: {res['p'].notna().sum()} (defined), "
                 f"{res['p'].isna().sum()} undefined (constant scores)")
    d = res[res["p"].notna()]
    lines.append(f"Significant at 0.05: Benjamini-Hochberg {int(d.sig.sum())}, "
                 f"Holm {int(d.sig_Holm.sum())}, Benjamini-Yekutieli {int(d.sig_BY.sum())} of {len(d)}")
    for name, col in [("Holm", "sig_Holm"), ("Benjamini-Yekutieli", "sig_BY")]:
        lost = d[d.sig & ~d[col]]
        if len(lost):
            lines.append(f"  Significant under BH but not {name}: " + "; ".join(
                f"{r.group} {r.dim} {r.pair} (rho {r.rho:+.3f}, q_BH {r.q_BH:.3g})" for r in lost.itertuples()))
        else:
            lines.append(f"  All BH-significant correlations remain significant under {name}")

    for t1, t2 in PAIRS:
        s_ = res[(res.pair == f"{t1}-{t2}") & (res.level == "sub-cloud")]
        M = s_.pivot(index="group", columns="dim", values="rho").reindex(index=clouds, columns=DIMS).values
        fig, ax = plt.subplots(figsize=(3.33, 3.0))
        im = heat(ax, M, clouds, [DIM_LABEL[d] for d in DIMS], "")
        ax.axvline(3.5, color="black", lw=0.6)
        fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03).outline.set_linewidth(.4)
        fig.savefig(f"{a.out}/fig_within_dimension_heatmap_{t1}-{t2}.pdf", bbox_inches="tight")
        fig.savefig(f"{a.out}/fig_within_dimension_heatmap_{t1}-{t2}.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

    print("2/5 pooled vs stratified", flush=True)
    strat = []
    pr = pu.copy()
    for d, t in itertools.product(DIMS, TOOLS):
        pr[f"{d}|{t}"] = pr.groupby("subcloud")[f"{d}|{t}"].transform(lambda s: rankdata(s) / len(s))
    for (t1, t2), d in itertools.product(PAIRS, DIMS):
        r_pool = res[(res.level == "pooled") & (res.pair == f"{t1}-{t2}") & (res.dim == d)]["rho"].iat[0]
        r_str = spearmanr(pr[f"{d}|{t1}"], pr[f"{d}|{t2}"])[0]
        strat.append(dict(pair=f"{t1}-{t2}", dim=d, pooled=r_pool, stratified=r_str))
    st = pd.DataFrame(strat); st.to_csv(f"{a.out}/pooled_vs_stratified.csv", index=False)
    fig, ax = plt.subplots(figsize=(3.33, 2.0))
    x = np.arange(len(DIMS)); wd = 0.13
    for k, (t1, t2) in enumerate(PAIRS):
        s = st[st.pair == f"{t1}-{t2}"].set_index("dim").reindex(DIMS)
        off = (k - 1) * 2.2 * wd
        ax.bar(x + off - wd / 2, s["pooled"], wd, color=light(PAIR_COLOR[f"{t1}-{t2}"], "66"), lw=0)
        ax.bar(x + off + wd / 2, s["stratified"], wd, color=PAIR_COLOR[f"{t1}-{t2}"], lw=0)
    ax.axhline(0, color=MUTED, lw=.5); ax.set_xticks(x, [DIM_LABEL[d] for d in DIMS])
    ax.set_ylabel("Spearman ρ"); ax.set_xlabel("FAIR dimension")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(f"{a.out}/fig_pooled_vs_stratified.pdf")
    fig.savefig(f"{a.out}/fig_pooled_vs_stratified.png", dpi=200); plt.close(fig)
    for _, r in st[st.dim == "composite"].iterrows():
        lines.append(f"Composite {r.pair}: pooled {r.pooled:+.3f} vs stratified {r.stratified:+.3f}")

    print("3/5 test-retest", flush=True)
    tr = []
    multi = df.groupby(["dataset_id", "tool"]).filter(lambda g: g["subcloud"].nunique() >= 2)
    for t in TOOLS:
        g = multi[multi.tool == t].copy()
        g["_o"] = g["subcloud"].map({s: i for i, s in enumerate(ORDER)}).fillna(99)
        g = g.sort_values(["dataset_id", "_o"])
        first = g.groupby("dataset_id").nth(0).set_index("dataset_id")
        second = g.groupby("dataset_id").nth(1).set_index("dataset_id")
        j = first.join(second, lsuffix="_1", rsuffix="_2", how="inner")
        if j.empty:
            continue
        j["diff"] = (j["composite_1"] - j["composite_2"]).abs()
        groups = {"all": j}
        if "url_1" in j:
            same = j["url_1"].fillna("") == j["url_2"].fillna("")
            groups.update({"same URL": j[same], "different URL": j[~same]})
        for name, s in groups.items():
            if len(s) == 0:
                continue
            r = spearmanr(s.composite_1, s.composite_2)[0] if len(s) > 3 and s.composite_1.std() and s.composite_2.std() else np.nan
            tr.append(dict(tool=t, subset=name, n=len(s), identical=int((s["diff"] < 1e-9).sum()),
                           max_abs_diff=s["diff"].max(), mean_abs_diff=s["diff"].mean(), rho=r))
    trd = pd.DataFrame(tr); trd.to_csv(f"{a.out}/test_retest.csv", index=False)
    if not trd.empty:
        for t in TOOLS:
            g = multi[multi.tool == t].copy()
            g["_o"] = g["subcloud"].map({s_: i for i, s_ in enumerate(ORDER)}).fillna(99)
            g = g.sort_values(["dataset_id", "_o"])
            p = g.groupby("dataset_id")["composite"].agg(lambda s_: list(s_)[:2])
            p = p[p.str.len() == 2]
            if p.empty:
                continue
            fig, ax = plt.subplots(figsize=(2.4, 2.4))
            ax.scatter([v[0] for v in p], [v[1] for v in p], s=7, alpha=.65, lw=0, c=TOOL_COLOR[t])
            ax.plot([0, 1], [0, 1], ls=":", c=MUTED, lw=.8)
            ax.set_xlabel("Composite score run 1"); ax.set_ylabel("Composite score run 2")
            ax.set_xlim(-.03, 1.03); ax.set_ylim(-.03, 1.03); ax.set_aspect("equal")
            fig.tight_layout()
            fig.savefig(f"{a.out}/fig_test_retest_{t}.pdf"); fig.savefig(f"{a.out}/fig_test_retest_{t}.png", dpi=200)
            plt.close(fig)
        for _, r in trd.iterrows():
            lines.append(f"Test-retest {r.tool} [{r.subset}]: n={r.n}, identical={r.identical}, "
                         f"max |diff|={r.max_abs_diff:.2f}, rho={r.rho:+.2f}")

    print("4/5 sensitivity", flush=True)
    wl = w.reset_index()
    wl["_o"] = wl["subcloud"].map({s: i for i, s in enumerate(ORDER)}).fillna(99)
    last = wl.sort_values("_o").drop_duplicates("dataset_id", keep="last")
    mean = wl.groupby("dataset_id")[[c for c in wl.columns if "|" in c]].mean()
    sens = []
    for (t1, t2), d in itertools.product(PAIRS, DIMS):
        sens.append(dict(pair=f"{t1}-{t2}", dim=d,
                         first=spearmanr(pu[f"{d}|{t1}"], pu[f"{d}|{t2}"])[0],
                         last=spearmanr(last[f"{d}|{t1}"], last[f"{d}|{t2}"])[0],
                         mean=spearmanr(mean[f"{d}|{t1}"], mean[f"{d}|{t2}"])[0]))
    sd = pd.DataFrame(sens); sd.to_csv(f"{a.out}/sensitivity.csv", index=False)
    spread = (sd[["first", "last", "mean"]].max(axis=1) - sd[["first", "last", "mean"]].min(axis=1)).max()
    lines.append(f"Sensitivity to first/last/mean assessment: max change in pooled rho = {spread:.3f}")

    print("5/5 BLOD top-10% overlap", flush=True)
    if "BLOD" in clouds:
        b = w.xs("BLOD", level="subcloud")
        for t1, t2 in PAIRS:
            k = max(1, int(round(0.10 * len(b)))); ov = []
            for _ in range(500):
                j1 = np.lexsort((RNG.random(len(b)), -b[f"composite|{t1}"].values))[:k]
                j2 = np.lexsort((RNG.random(len(b)), -b[f"composite|{t2}"].values))[:k]
                ov.append(len(set(j1) & set(j2)) / k)
            lines.append(f"BLOD top-10% overlap {t1}-{t2}: {np.mean(ov):.1%} (chance 10%)")

    open(f"{a.out}/summary.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
