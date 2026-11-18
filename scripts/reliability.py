"""Reusable finite-sample calibration and grouped reliability diagnostics."""
import numpy as np
import pandas as pd

METHODS=['pooled','one_per_study','study_max','label_conditional']

def quantile(scores,alpha):
    scores=np.asarray(scores,float)
    k=int(np.ceil((len(scores)+1)*(1-alpha)))
    return float(np.sort(scores)[k-1]) if 0<k<=len(scores) else np.inf

def thresholds(cal,method,alpha,seed=20261118):
    s=np.where(cal.y.to_numpy()==1,1-cal.p.to_numpy(),cal.p.to_numpy())
    d=pd.DataFrame({'study':cal.study.to_numpy(),'score':s,'y':cal.y.to_numpy()})
    if method=='label_conditional':return tuple(quantile(d.loc[d.y==c,'score'],alpha) for c in [0,1])
    if method=='pooled':scores=s
    elif method=='study_max':scores=d.groupby('study',sort=True).score.max().to_numpy()
    elif method=='one_per_study':
        rng=np.random.default_rng(seed)
        scores=[rng.choice(x.score.to_numpy()) for _,x in d.groupby('study',sort=True)]
    else:raise ValueError(method)
    q=quantile(scores,alpha);return q,q

def sets(p,qs):
    p=np.asarray(p,float)
    return (p<=qs[0]).astype(int)+2*((1-p)<=qs[1]).astype(int)

def summary(frame,codes):
    y=frame.y.to_numpy(dtype=int);codes=np.asarray(codes,int)
    covered=(codes & (1<<y))>0;single=np.isin(codes,[1,2]);wrong=single&~covered
    groups=pd.DataFrame({'study':frame.study.to_numpy(),'covered':covered,'single':single,'wrong':wrong}).groupby('study')
    n0=int((y==0).sum());n1=int((y==1).sum());ns=int(single.sum())
    return {'n':len(y),'studies':frame.study.nunique(),'positive':n1,'row_coverage':float(covered.mean()),
            'study_coverage':float(groups.covered.mean().mean()),'whole_coverage':float(groups.covered.all().mean()),
            'coverage_negative':float(covered[y==0].mean()) if n0 else np.nan,
            'coverage_positive':float(covered[y==1].mean()) if n1 else np.nan,
            'singleton_rate':float(single.mean()),'singleton_n':ns,'singleton_errors':int(wrong.sum()),
            'singleton_error':float(wrong.sum()/ns) if ns else np.nan,
            'false_negative_n':int(((codes==1)&(y==1)).sum()),
            'false_negative_fraction':float(((codes==1)&(y==1)).sum()/n1) if n1 else np.nan,
            'empty_rate':float((codes==0).mean()),'mean_set_size':float(((codes&1)+((codes>>1)&1)).mean())}
