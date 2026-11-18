"""Executed extension contrasts and uncertainty, with source-cluster resampling."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/v2';SEED=20261118

def main():
    d=pd.read_csv(OUT/'predictions.csv');contrast=[];detectors=[];correlations=[]
    for regime,g in d.groupby('regime'):
        g=g.copy();g['wrong']=((g.p>=.5)!=g.y).astype(int);g['loss']=(g.p-g.y)**2
        detectors.append({'regime':regime,'n':len(g),'error_prevalence':g.wrong.mean(),
                          'distance_error_auc':roc_auc_score(g.wrong,g.distance),
                          'uncertainty_error_auc':roc_auc_score(g.wrong,1-np.maximum(g.p,1-g.p)),
                          'unknown_fraction':(g.unknown_categories>0).mean()})
        rows=[]
        for _,s in g.groupby('study',sort=True):
            y=s.y.to_numpy(int);p=s['set_pooled_0.10'].to_numpy(int);m=s['set_label_conditional_0.10'].to_numpy(int)
            hp=(p&(1<<y))>0;hm=(m&(1<<y))>0
            unknown=s.unknown_categories>0;known=~unknown
            rows.append([int((y==0).sum()),int((y==1).sum()),int(((hm.astype(int)-hp.astype(int))*(y==0)).sum()),int(((hm.astype(int)-hp.astype(int))*(y==1)).sum()),
                         int(known.sum()),int(unknown.sum()),float(s.loc[known,'loss'].sum()),float(s.loc[unknown,'loss'].sum()),
                         int(s.loc[known,'wrong'].sum()),int(s.loc[unknown,'wrong'].sum())])
        a=np.asarray(rows);rng=np.random.default_rng(SEED);idx=rng.integers(0,len(a),(2000,len(a)));b=a[idx].sum(axis=1);tot=a.sum(axis=0)
        definitions=[('label_conditional_minus_pooled_negative_coverage',lambda x:x[...,2]/x[...,0]),
                     ('label_conditional_minus_pooled_positive_coverage',lambda x:x[...,3]/x[...,1]),
                     ('unknown_minus_known_brier',lambda x:x[...,7]/x[...,5]-x[...,6]/x[...,4]),
                     ('unknown_minus_known_error',lambda x:x[...,9]/x[...,5]-x[...,8]/x[...,4])]
        for metric,f in definitions:
            with np.errstate(divide='ignore',invalid='ignore'):v=f(b);estimate=f(tot)
            contrast.append({'regime':regime,'contrast':metric,'estimate':float(estimate),'lo':float(np.nanquantile(v,.025)),'hi':float(np.nanquantile(v,.975)),'bootstrap_sources':len(a)})
        source=g.groupby('study').agg(n=('y','size'),distance=('distance','mean'),brier=('loss','mean'))
        for variable in ['n','distance']:
            correlations.append({'regime':regime,'variable':variable,'outcome':'source_brier','sources':len(source),'spearman_r':spearmanr(source[variable],source.brier).statistic})
    pd.DataFrame(contrast).to_csv(OUT/'contrasts.csv',index=False);pd.DataFrame(detectors).to_csv(OUT/'error_detection.csv',index=False)
    pd.DataFrame(correlations).to_csv(OUT/'source_correlations.csv',index=False)
    raw=pd.read_csv(ROOT/'data/processed/canonical.csv')
    quality=[]
    for pub,status in [(13,'unresolved primary full text'),(84,'unresolved concentration conversion'),(87,'high-dose units confirmed against primary Figure 1 and Table 1')]:
        x=raw[raw.publication_id==pub]
        quality.append({'publication_id':pub,'n':len(x),'flagged_n':int((x.dose_ug_ml>10000).sum()),'max_ug_ml':float(x.dose_ug_ml.max()),'status':status})
    pd.DataFrame(quality).to_csv(OUT/'unit_verification.csv',index=False)
    report={'error_detection':detectors,'contrasts':contrast,'quality':quality,'learning':json.loads(pd.read_csv(OUT/'learning_curve.csv').query('method == "pooled"').groupby('fitting_sources')[['auc','brier']].agg(['min','median','max']).to_json()),'no_new_p_values':True}
    (OUT/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(pd.DataFrame(detectors).round(4).to_string(index=False));print(pd.DataFrame(contrast).round(4).to_string(index=False))

if __name__=='__main__':main()
