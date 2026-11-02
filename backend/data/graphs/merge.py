import argparse, os, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

SUBCLOUD = {
    "blod": "BLOD", "che-cloud": "CHeCLOUD", "cross-domain": "Cross-domain",
    "geography": "Geography", "government": "Government", "life-sciences": "Life Sciences",
    "linguistic": "Linguistic", "media": "Media", "publications": "Publications",
    "social-networking": "Social Networking", "user-generated": "User Generated",
}
PRINCIPLES = ["F1", "F2", "F3", "A1", "A1.2", "I1", "I2", "I3", "R1.1", "R1.2", "R1.3"]
DIMS = {"F": ["F1", "F2", "F3"], "A": ["A1", "A1.2"], "I": ["I1", "I2", "I3"], "R": ["R1.1", "R1.2", "R1.3"]}

FC_MAP = {
    "F1": [("score_F1A", 2), ("score_F1B", 2)],
    "F2": [("score_F2A", 2), ("score_F2B", 2)],
    "A1": [("score_A1.1", 2)], "A1.2": [("score_A1.2", 2)],
    "I1": [("score_I1", 2)], "I2": [("score_I2", 2)], "I3": [("score_I3", 2)],
    "R1.1": [("score_R1.1", 2)], "R1.2": [("score_R1.2", 2)], "R1.3": [("score_R1.3", 2)],
}
FU_MAP = {
    "F1": [("FsF_F1_01MD_earned", 1), ("FsF_F1_02MD_earned", 1)],
    "F2": [("FsF_F2_01M_earned", 2)],
    "F3": [("FsF_F3_01M_earned", 1)],
    "A1": [("FsF_A1_02MD_earned", 2), ("FsF_A1_1_01MD_earned", 2)],
    "A1.2": [("FsF_A1_2_01MD_earned", 2)],
    "I1": [("FsF_I1_01M_earned", 2)], "I2": [("FsF_I2_01M_earned", 2)], "I3": [("FsF_I3_01M_earned", 2)],
    "R1.1": [("FsF_R1_1_01M_earned", 1)], "R1.2": [("FsF_R1_2_01M_earned", 1)],
    "R1.3": [("FsF_R1_3_01M_earned", 1), ("FsF_R1_3_02D_earned", 1)],
}
KG_MAP = {
    "F1": ["F1-M", "F1-D"], "F2": ["F2a-M", "F2b-M"], "F3": ["F3-M"],
    "A1": ["A1-D", "A1-M"], "A1.2": ["A1.2"],
    "I1": ["I1-D", "I1-M"], "I2": ["I2"], "I3": ["I3-D"],
    "R1.1": ["R1.1"], "R1.2": ["R1.2"], "R1.3": ["R1.3-D", "R1.3-M"],
}


KG_FEATURES = {"pid_doi": "F3-M", "metadata_completeness": "F2b-M",
               "interlinked": "I3-D", "endpoint": "A1-D"}


def read(path):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except UnicodeDecodeError:
            continue
    sys.exit(f"cannot read {path}")


def num(s):
    return pd.to_numeric(s, errors="coerce")


def score_points(df, mapping, tool, sub, report):
    out = pd.DataFrame(index=df.index)
    for p, metrics in mapping.items():
        cols = []
        for col, pts in metrics:
            if col not in df:
                sys.exit(f"[{tool}/{sub}] column not found: {col}")
            v = num(df[col])
            over = int((v > pts).sum())
            if over:
                report.append(f"  {tool:12s} {sub:18s} {col}: {over} value(s) above {pts}, capped at 1")
            cols.append((v / pts).clip(upper=1))
        out[p] = pd.concat(cols, axis=1).mean(axis=1, skipna=False)
    return out


def score_kg(df, sub, report):
    code = {c.strip().split()[0]: c for c in df.columns}
    out = pd.DataFrame(index=df.index)
    for p, metrics in KG_MAP.items():
        miss = [m for m in metrics if m not in code]
        if miss:
            sys.exit(f"[KGHeartBeat/{sub}] columns not found for {miss}; have {list(code)}")
        out[p] = pd.concat([num(df[code[m]]).clip(0, 1) for m in metrics], axis=1).mean(axis=1, skipna=False)
    for name, m in KG_FEATURES.items():
        out[name] = num(df[code[m]]).clip(0, 1) if m in code else np.nan
    return out


def key(v):
    if not isinstance(v, str):
        return ""
    return re.sub(r"[\s_\-]+", "-", v.strip().lower()).strip("-")


def load_tool(folder, tool, report):
    frames = []
    for f in sorted(Path(folder).glob("*.csv")):
        sub = SUBCLOUD.get(f.stem.lower())
        if sub is None:
            report.append(f"  skipped {f.name}: unknown sub-cloud name")
            continue
        df = read(f)
        df.columns = [c.strip() for c in df.columns]
        if tool == "FAIR-Checker":
            ids, url = df["id"], df.get("processed_url")
            s = score_points(df, FC_MAP, tool, sub, report)
        elif tool == "F-UJI":
            ids, url = df["id"], df.get("url")
            s = score_points(df, FU_MAP, tool, sub, report)
        else:
            idc = "KG id" if "KG id" in df else "id"
            ids, url = df[idc], df.get("Dataset URL")
            s = score_kg(df, sub, report)
        s.insert(0, "dataset_id", ids.map(key))
        s["title"] = df["KG name"].map(key) if "KG name" in df else ""
        s.insert(1, "subcloud", sub)
        s.insert(2, "tool", tool)
        s["url"] = url.str.strip() if url is not None else np.nan
        dup = s.duplicated(["dataset_id", "subcloud"]).sum()
        if dup:
            report.append(f"  {tool:12s} {sub:18s} {dup} duplicate id(s), kept first")
            s = s.drop_duplicates(["dataset_id", "subcloud"])
        failed = s[PRINCIPLES].isna().all(axis=1) if tool != "FAIR-Checker" else s[[p for p in PRINCIPLES if p != "F3"]].isna().all(axis=1)
        if failed.any():
            report.append(f"  {tool:12s} {sub:18s} no result for {failed.sum()}: {', '.join(s.loc[failed, 'dataset_id'])}")
        frames.append(s[~failed])
    if not frames:
        sys.exit(f"no CSVs found in {folder}")
    return pd.concat(frames, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("raw", nargs="?", default=str(here.parent / "raw"))
    ap.add_argument("--out", default=str(here / "scores.csv"))
    a = ap.parse_args()
    raw = Path(a.raw)
    report = ["Notes:"]
    parts = [load_tool(raw / "fairchecker", "FAIR-Checker", report),
             load_tool(raw / "fuji", "F-UJI", report),
             load_tool(raw / "kgheartbeat", "KGHeartBeat", report)]
    fc, fu, kg = parts
    kg = kg.copy()
    by_title = 0
    for sub in kg["subcloud"].unique():
        ref = set(fc.loc[fc.subcloud == sub, "dataset_id"]) & set(fu.loc[fu.subcloud == sub, "dataset_id"])
        m = (kg.subcloud == sub) & ~kg["dataset_id"].isin(ref) & kg["title"].isin(ref)
        m &= ~kg.loc[:, "title"].where(m).isin(kg.loc[kg.subcloud == sub, "dataset_id"])
        kg.loc[m, "dataset_id"] = kg.loc[m, "title"]
        by_title += int(m.sum())
    kg = kg.drop(columns="title").drop_duplicates(["dataset_id", "subcloud"])
    report.append(f"  KGHeartBeat rows matched by id: {len(kg) - by_title}, by title: {by_title}")
    long = pd.concat([fc, fu, kg], ignore_index=True)

    pcols = [p for p in PRINCIPLES]
    partial = long[pcols].isna() & ~((long.tool == "FAIR-Checker").values[:, None] & (np.array(pcols) == "F3"))
    if partial.values.any():
        report.append(f"  {int(partial.any(axis=1).sum())} row(s) with some non-numeric metric values, set to 0")
        for p in pcols:
            m = partial[p]
            long.loc[m, p] = 0.0

    present = long.groupby(["dataset_id", "subcloud"])["tool"].nunique()
    keep = present[present == 3].index
    dropped = present[present < 3]
    for sub, g in dropped.groupby(level="subcloud"):
        report.append(f"  {sub:18s} dropped {len(g)} dataset(s) not scored by all three tools")
    long = long.set_index(["dataset_id", "subcloud"]).loc[keep].reset_index()

    is_http = long["url"].fillna("").str.match(r"https?://")
    has_url = long[long.tool.isin(["FAIR-Checker", "KGHeartBeat"])].assign(h=is_http) \
        .groupby(["dataset_id", "subcloud"])["h"].any()
    no_url = has_url[~has_url].index
    no_url_blod = [i for i in no_url if i[1] == "BLOD"]
    if no_url_blod:
        report.append(f"  BLOD               dropped {len(no_url_blod)} KG(s) with no http(s) URL: "
                      + ", ".join(i[0] for i in no_url_blod))
        long = long.set_index(["dataset_id", "subcloud"]).drop(no_url_blod).reset_index()

    for d, ps in DIMS.items():
        long[d] = long[ps].mean(axis=1, skipna=True)
    long["composite"] = long[list(DIMS)].mean(axis=1)

    cols = ["dataset_id", "subcloud", "tool", "F", "A", "I", "R", "composite", "url"] + PRINCIPLES
    long[cols].sort_values(["subcloud", "dataset_id", "tool"]).to_csv(a.out, index=False)
    feats = long.loc[long.tool == "KGHeartBeat", ["dataset_id", "subcloud"] + list(KG_FEATURES)]
    feat_path = os.path.join(os.path.dirname(os.path.abspath(a.out)), "kg_features.csv")
    feats.sort_values(["subcloud", "dataset_id"]).to_csv(feat_path, index=False)

    n = long.groupby("subcloud")["dataset_id"].nunique()
    mean = long.pivot_table(index="subcloud", columns="tool", values="composite", aggfunc="mean")
    chk = pd.concat([n.rename("n"), mean.round(2)], axis=1)
    print("\n".join(report))
    print("\nPer sub-cloud (compare n with Table 5, means with Finding 10 / Figure 3):")
    print(chk.to_string())
    print(f"\nTotal assessments: {n.sum()}   unique datasets: {long['dataset_id'].nunique()}")
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()
