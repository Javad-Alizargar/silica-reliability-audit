"""Complement degenerate bootstrap coverage intervals with source-binomial intervals."""
from pathlib import Path
import json
import pandas as pd
from scipy.stats import beta

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"results/set_performance.csv"
d=pd.read_csv(p)
for i,row in d[d.regime.str.startswith("external")].iterrows():
    n=int(row.studies);k=round(row.whole_study_coverage*n)
    d.loc[i,"whole_study_exact_lo"]=0 if k==0 else beta.ppf(.025,k,n-k+1)
    d.loc[i,"whole_study_exact_hi"]=1 if k==n else beta.ppf(.975,k+1,n-k)
d.to_csv(p,index=False)
s=json.loads((ROOT/"results/statistics.json").read_text())
s["primary_external_sets"]=json.loads(d[(d.model=="random_forest")&(d.regime=="external")&(d.alpha==.1)].to_json(orient="records"))
s["interval_amendment"]="Exact Clopper-Pearson intervals added for external whole-study coverage after observing degenerate percentile bootstrap intervals at 26/26 successes. They assume independent exchangeable external study outcomes conditional on the fitted model; they are not distribution-shift guarantees."
(ROOT/"results/statistics.json").write_text(json.dumps(s,indent=2,allow_nan=False))
print(d[(d.model=="random_forest")&(d.regime=="external")&(d.alpha==.1)][["method","whole_study_coverage","whole_study_exact_lo","whole_study_exact_hi"]].to_string(index=False))
