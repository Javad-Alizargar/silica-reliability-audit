"""Read immutable publisher workbook; produce auditable canonical data."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = {
    "Primary_size_nm": "size_nm", "Concentration_µg/ml": "dose_ug_ml",
    "Exposure_time_h": "time_h", "SiO$_{2}$NP_medium_serum": "serum",
    "Surface_modification": "surface", "SiO$_{2}$NP_shape": "shape",
    "SiO$_{2}$NP_synthesis": "synthesis", "Cell_source": "species",
    "Cell_id": "cell", "Cell_disease": "disease", "Exposure_medium": "medium",
    "Assay_viability": "assay"
}

def main():
    (ROOT / 'results').mkdir(exist_ok=True)
    path = ROOT / "download/nn2c11968_si_003.xlsx"
    refs = pd.read_excel(path, "References", header=None)
    refs = refs.loc[pd.to_numeric(refs[0], errors="coerce").notna(), [0,1,2,3]].copy()
    refs.columns = ["publication_id", "author", "year", "doi"]
    refs["publication_id"] = refs.publication_id.astype(int)
    refs["doi"] = refs.doi.fillna("").astype(str).str.strip().str.lower()
    refs["study"] = [f"doi:{d}" if d else f"source:{i}" for i,d in zip(refs.publication_id,refs.doi)]
    refs = refs.set_index("publication_id")
    tables, audits = [], []
    dictionary = []
    for cohort, sheet, target in [("development", "Main_Dataset", "Cell_viability"),
                                  ("external", "Independent_Dataset", "Cell_viability.1")]:
        raw = pd.read_excel(path, sheet)
        raw.columns = raw.columns.str.strip()
        duplicate = raw.duplicated(keep="first")
        df = raw.loc[~duplicate].copy()
        out = df[list(FEATURES)].rename(columns=FEATURES)
        for col in out:
            if col in ["size_nm", "dose_ug_ml", "time_h"]:
                out[col] = pd.to_numeric(out[col], errors="raise")
                assert (out[col] >= 0).all()
            else:
                out[col] = out[col].astype(str).str.strip()
        out["row_id"] = [f"{cohort}:{i+2}" for i in df.index]
        out["publication_id"] = df.Publication_id.astype(int)
        out["study"] = out.publication_id.map(refs.study)
        out["year"] = out.publication_id.map(refs.year)
        out["cohort"] = cohort
        out["y"] = df[target].map({"Non_cytotoxic":0,"Cytotoxic":1})
        assert out.y.notna().all() and out.study.notna().all()
        out["profile"] = pd.util.hash_pandas_object(out[list(FEATURES.values())], index=False).astype(str)
        audit = {"cohort":cohort,"original_n":len(raw),"n":len(out),"duplicates_removed":int(duplicate.sum()),
                 "studies":out.study.nunique(),"positive":int(out.y.sum()),"nanoscale_n":int((out.size_nm<=100).sum()),
                 "range_size_nm":[float(out.size_nm.min()),float(out.size_nm.max())],
                 "range_dose_ug_ml":[float(out.dose_ug_ml.min()),float(out.dose_ug_ml.max())],
                 "range_time_h":[float(out.time_h.min()),float(out.time_h.max())]}
        if cohort == "external":
            audit["continuous_label_disagreements"] = int(((df["Cell_viability"]<70).astype(int)!=out.y).sum())
            audit["in_house_n"] = int((out.publication_id==116).sum())
        for col in out[list(FEATURES.values())]:
            dictionary.append({"cohort":cohort,"variable":col,"n":len(out),"distinct":out[col].nunique(),
                               "null_n":int(out[col].isna().sum()),
                               "not_determined_n":int(out[col].astype(str).str.contains("not_determined|not_available",regex=True).sum())})
        tables.append(out)
        audits.append(audit)
    dev, ext = tables
    assert not set(dev.study)&set(ext.study), "Same DOI/source appears in both cohorts"
    ext["overlap_profile"] = ext.profile.isin(dev.profile)
    dev["overlap_profile"] = False
    summary = {"cohorts":audits,"overlapping_source_groups":0,"external_matching_profile_n":int(ext.overlap_profile.sum()),
               "raw_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
               "feature_columns":list(FEATURES.values()),
               "interpretation":"Repeated experimental conditions; source IDs are not laboratory IDs."}
    (ROOT/"data/processed").mkdir(parents=True,exist_ok=True)
    pd.concat(tables,ignore_index=True).to_csv(ROOT/"data/processed/canonical.csv",index=False)
    refs.to_csv(ROOT/"data/processed/study_dictionary.csv")
    pd.DataFrame(dictionary).to_csv(ROOT/"results/data_dictionary.csv",index=False)
    pd.DataFrame(audits).to_csv(ROOT/"results/cohort_summary.csv",index=False)
    (ROOT/"results/data_audit.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__": main()
