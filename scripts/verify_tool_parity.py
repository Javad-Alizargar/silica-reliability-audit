"""Independent result comparison: JavaScript math vs frozen Python research results."""
from pathlib import Path
import json, math
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/v2/tool_math_results.json').read_text())['real_data']
cp=pd.read_csv(ROOT/'results/v2/calibration_performance.csv').query("regime == 'external' and alpha == 0.1").set_index('method')
checks=[]
for method in ['pooled','study_max','label_conditional']:
    js=r['results'][method];p=cp.loc[method]
    for name,pyname in [('row_coverage','row_coverage'),('whole_source_coverage','whole_coverage'),('singleton_rate','singleton_rate'),('singleton_error','singleton_error'),('mean_set_size','mean_set_size'),('false_negative_fraction','false_negative_fraction')]:
        assert abs(js[name]-p[pyname])<1e-12,(method,name);checks.append(method+':'+name)
    for c,col in enumerate(['coverage_negative','coverage_positive']):
        assert abs(js['class_coverage'][c]-p[col])<1e-12;checks.append(method+':'+col)
# Independently reproduce the documented browser RNG; the research NumPy sampler differs.
cal=pd.read_csv(ROOT/'website/example.csv').query("role == 'calibration'")
state=20261118;selected=[];scores=[]
for source,g in cal.groupby('study',sort=True):
    state=(1664525*state+1013904223)%(2**32)
    row=g.iloc[math.floor(state/(2**32)*len(g))];selected.append(row.row_id)
    scores.append(row.p if row.y==0 else 1-row.p)
assert selected==r['results']['one_per_study']['selected'];checks.append('LCG selected row IDs')
q=sorted(scores)[math.ceil((len(scores)+1)*.9)-1]
assert abs(q-r['results']['one_per_study']['q'][0])<1e-12;checks.append('LCG quantile')
(ROOT/'reports/v2/TOOL_PARITY.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'scope':'Frozen external predictions; independent Python aggregate and sampling comparisons'},indent=2))
print(len(checks),'independent cross-language comparisons passed.')
