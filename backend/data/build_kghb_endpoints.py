"""
build_kghb_endpoints.py
=======================
Extracts the SPARQL endpoint of every knowledge graph from a KGHeartBeat
analysis snapshot (the daily CSV, e.g. 2026-06-07.csv) into the small file
data/kghb_sparql_endpoints.csv that the backend reads.

KGHeartBeat records, per KG:
  "SPARQL endpoint URL"  the endpoint declared in the KG's metadata
  "Sparql endpoint"      its check result: "Available", "offline", or "-"
                         ("-" with a URL means the check could not reach it)

Output columns: id, endpoint_url, status (online | offline | unreachable), checked_on

It also writes data/kghb_metadata.csv (id, name, description) from the same
snapshot, used for topic search in /federated/select for datasets that are not
in BLOD.json.

Only URLs that look like SPARQL endpoints are kept, unless KGHeartBeat found
them online (declared endpoints sometimes point at web pages or documents).

Usage (from backend/):
    python data/build_kghb_endpoints.py /path/to/2026-06-07.csv
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

OUT = Path(__file__).parent / "kghb_sparql_endpoints.csv"
META_OUT = Path(__file__).parent / "kghb_metadata.csv"

ENDPOINT_HINT = re.compile(r"sparql|/query|endpoint|repositories|snorql|squery", re.I)
JUNK = re.compile(r"example\.(org|com)|/wp-json/|disk\.yandex|dbpedia\.org/page/|\.pdf$", re.I)
STATUS = {"available": "online", "offline": "offline"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot_csv", help="KGHeartBeat analysis CSV, e.g. 2026-06-07.csv")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--metadata-out", default=str(META_OUT))
    a = ap.parse_args()

    checked_on = re.search(r"\d{4}-\d{2}-\d{2}", Path(a.snapshot_csv).name)
    checked_on = checked_on.group(0) if checked_on else ""

    df = pd.read_csv(a.snapshot_csv, low_memory=False,
                     usecols=["KG id", "KG name", "Description", "Sparql endpoint", "SPARQL endpoint URL"])

    meta = pd.DataFrame({
        "id": df["KG id"].astype(str).str.strip(),
        "name": df["KG name"].fillna("").astype(str).str.strip(),
        "description": df["Description"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip(),
    })
    meta.loc[meta["description"].isin(["-", "nan"]), "description"] = ""
    meta = meta.drop_duplicates(subset="id")
    meta.to_csv(a.metadata_out, index=False)
    print(f"{len(meta)} dataset names/descriptions written to {a.metadata_out} "
          f"({(meta.description != '').sum()} with a description)")
    rows, dropped = [], 0
    for _, r in df.iterrows():
        url = str(r["SPARQL endpoint URL"]).strip() if pd.notna(r["SPARQL endpoint URL"]) else ""
        if not url.startswith(("http://", "https://")) or " " in url:
            continue
        status = STATUS.get(str(r["Sparql endpoint"]).strip().lower(), "unreachable")
        if JUNK.search(url) or (status != "online" and not ENDPOINT_HINT.search(url)):
            dropped += 1
            continue
        rows.append({"id": str(r["KG id"]).strip(), "endpoint_url": url, "status": status, "checked_on": checked_on})

    out = pd.DataFrame(rows).drop_duplicates(subset=["id", "endpoint_url"])
    out.to_csv(a.out, index=False)
    print(f"{len(out)} endpoints written to {a.out} "
          f"({(out.status == 'online').sum()} online, {(out.status == 'offline').sum()} offline, "
          f"{(out.status == 'unreachable').sum()} unreachable); {dropped} non-endpoint URLs dropped")


if __name__ == "__main__":
    main()
