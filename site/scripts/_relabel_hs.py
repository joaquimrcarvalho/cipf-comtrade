"""One-off maintenance: re-apply HS_PT labels to all profile CSVs and rebuild
hs_ag6_labels.json, then report remaining PT-label collisions.

Run after editing HS_PT in export_profiles.py:

    venv/bin/python site/scripts/_relabel_hs.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import export_profiles as ep  # noqa: E402

ctt = ep.init_comtradetools()
data = ep.OUT_DIR

changed_cells = 0
for csv in sorted(data.glob("*.csv")):
    df = pd.read_csv(csv, dtype={"hs6": str})
    if "hs6" not in df.columns or "description_pt" not in df.columns:
        continue
    new = df["hs6"].map(lambda c: ep.hs_label_pt(ctt, str(c)))
    diff = (new != df["description_pt"]) & new.notna()
    if diff.any():
        df.loc[diff, "description_pt"] = new[diff]
        df.to_csv(csv, index=False)
        changed_cells += int(diff.sum())
print(f"relabeled {changed_cells} cells")

codes = set()
for pattern in ("*_top_products_*_HS-AG6_*.csv", "*_products_partners_HS-AG6_*.csv",
                "*_partners_products_HS-AG6_*.csv", "*_competition_*_HS-AG6_*.csv"):
    for csv in data.glob(pattern):
        if csv.name.startswith(("cn_", "mo_", "hk_")):
            continue
        try:
            codes.update(pd.read_csv(csv, usecols=["hs6"], dtype=str)["hs6"].unique())
        except Exception:
            continue
rows = []
for code in sorted(codes):
    en = ctt.HS_CODES.get(code)
    if not isinstance(en, str):
        en = code
    rows.append({"hs6": code, "en": en, "pt": ep.HS_PT.get(code, ep.HS_PT.get(code[:4]))})
(data / "hs_ag6_labels.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

coll = {}
for r in rows:
    if r["pt"]:
        coll.setdefault(r["pt"], set()).add(r["hs6"])
dup = {k: sorted(v) for k, v in coll.items() if len(v) > 1}
print(f"codes: {len(rows)} | colliding PT labels: {len(dup)}")
for k, v in sorted(dup.items()):
    print("  ", k, "<-", ", ".join(v))

print("\nArroz group:")
for r in rows:
    if r["hs6"].startswith("1006"):
        print("  ", r["hs6"], "->", r["pt"])
print("\n7214xx/721590:")
for r in rows:
    if r["hs6"] in ("721420", "721491", "721499", "721590"):
        print("  ", r["hs6"], "->", r["pt"])
