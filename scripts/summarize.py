"""Aggregate saved held-out predictions, with source-cluster uncertainty."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, balanced_accuracy_score

ROOT=Path(__file__).resolve().parents[1]
B=2000
SEED=20261118

def metrics(d):
    y=d.y.to_numpy();p=d.p.to_numpy();loss=(y-p)**2
    g=pd.DataFrame({"study":d.study.to_numpy(),"loss":loss}).groupby("study").loss.mean()
    return {"n":len(d),"studies":d.study.nunique(),"positive":int(y.sum()),
            "auc":roc_auc_score(y,p) if len(set(y))==2 else np.nan,
            "average_precision":average_precision_score(y,p),"brier":loss.mean(),
            "study_brier":g.mean(),"balanced_accuracy":balanced_accuracy_score(y,p>=.5)}

def set_summary(d,method,alpha):
    code=d[f"set_{method}_{alpha:.2f}"].to_numpy().astype(int)
    y=d.y.to_numpy().astype(int)
    contains=((code & (1<<y))>0).astype(int)
    singleton=np.isin(code,[1,2]).astype(int)
    wrong=singleton*(1-contains)
    false_negative=((code==1)&(y==1)).astype(int)
    size=(code&1)+((code>>1)&1)
    base=pd.DataFrame({"study":d.study.to_numpy(),"n":1,"covered":contains,"singleton":singleton,
                       "wrong":wrong,"false_negative":false_negative,"positive":y,"size":size,"empty":code==0})
    group=base.groupby("study").sum()
    group["study_coverage"]=base.groupby("study").covered.mean()
    group["whole_study"]=base.groupby("study").covered.min()
    totals=group.sum()
    out={"n":len(d),"studies":len(group),"row_coverage":totals.covered/totals.n,
         "study_coverage":group.study_coverage.mean(),"whole_study_coverage":group.whole_study.mean(),
         "singleton_rate":totals.singleton/totals.n,"singleton_n":int(totals.singleton),
         "singleton_errors":int(totals.wrong),
         "singleton_error":totals.wrong/totals.singleton if totals.singleton else np.nan,
         "false_negative_singleton_rate":totals.false_negative/totals.singleton if totals.singleton else np.nan,
         "mean_set_size":totals['size']/totals.n,"empty_rate":totals['empty']/totals.n}
    return out,group

def set_ci(group):
    rng=np.random.default_rng(SEED)
    idx=rng.integers(0,len(group),(B,len(group)))
    boot={}
    for metric,col in [("study_coverage","study_coverage"),("whole_study_coverage","whole_study")]:
        boot[metric]=group[col].to_numpy()[idx].mean(axis=1)
    for metric,num,den in [("row_coverage","covered","n"),("singleton_rate","singleton","n"),
                            ("singleton_error","wrong","singleton"),("mean_set_size","size","n")]:
        a=group[num].to_numpy()[idx].sum(axis=1);b=group[den].to_numpy()[idx].sum(axis=1)
        boot[metric]=np.divide(a,b,out=np.full(B,np.nan),where=b>0)
    return {f"{k}_{end}":float(np.nanquantile(v,q)) for k,v in boot.items() for end,q in [("lo",.025),("hi",.975)]}

def model_ci(d):
    rng=np.random.default_rng(SEED)
    groups=[x.index.to_numpy() for _,x in d.reset_index(drop=True).groupby("study",sort=True)]
    y=d.y.to_numpy();p=d.p.to_numpy();loss=(y-p)**2
    auc=[];brier=[]
    for _ in range(B):
        idx=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))])
        auc.append(roc_auc_score(y[idx],p[idx]) if len(np.unique(y[idx]))==2 else np.nan)
        brier.append(loss[idx].mean())
    return {f"{k}_{end}":float(np.nanquantile(v,q)) for k,v in [("auc",auc),("brier",brier)] for end,q in [("lo",.025),("hi",.975)]}

def main():
    d=pd.read_csv(ROOT/"results/predictions.csv")
    primary=d[d.repeat==0]
    rows=[]
    for (regime,model),g in primary.groupby(["regime","model"],sort=True):
        v={"regime":regime,"model":model,**metrics(g)}
        if regime in ["row","study","external"]: v.update(model_ci(g))
        rows.append(v)
    perf=pd.DataFrame(rows);perf.to_csv(ROOT/"results/model_performance.csv",index=False)
    sets=[];perstudy=[]
    for (regime,model),g in primary.groupby(["regime","model"],sort=True):
        for method in ["pooled","one_per_study","study_max"]:
            for alpha in [.05,.10,.20]:
                v,group=set_summary(g,method,alpha)
                if model=="random_forest" and regime in ["row","study","external"]:v.update(set_ci(group))
                sets.append({"regime":regime,"model":model,"method":method,"alpha":alpha,**v})
                group=group.reset_index();group["regime"]=regime;group["model"]=model;group["method"]=method;group["alpha"]=alpha
                perstudy.append(group)
    sets=pd.DataFrame(sets);sets.to_csv(ROOT/"results/set_performance.csv",index=False)
    pd.concat(perstudy,ignore_index=True).to_csv(ROOT/"results/per_study_sets.csv",index=False)
    sensitivity=[]
    rf=d[(d.model=="random_forest") & (d.regime=="external")]
    for repeat,g in rf.groupby("repeat"):
        subsets={"all":g,"literature_only":g[g.publication_id!=116],"size_le100":g[g.size_nm<=100],"unmatched_profiles":g[~g.overlap_profile.astype(bool)]}
        for subset,t in subsets.items():
            for method in ["pooled","one_per_study","study_max"]:
                v,_=set_summary(t,method,.10)
                sensitivity.append({"repeat":repeat,"subset":subset,"method":method,**metrics(t),**v})
    pd.DataFrame(sensitivity).to_csv(ROOT/"results/sensitivity.csv",index=False)
    repeats=[]
    for (regime,repeat,model),g in d.groupby(["regime","repeat","model"]):
        repeats.append({"regime":regime,"repeat":repeat,"model":model,**metrics(g)})
    pd.DataFrame(repeats).to_csv(ROOT/"results/repeat_performance.csv",index=False)
    ext=primary[(primary.regime=="external")&(primary.model=="random_forest")]
    a,ga=set_summary(ext,"pooled",.10);b,gb=set_summary(ext,"study_max",.10)
    assert ga.index.equals(gb.index)
    rng=np.random.default_rng(SEED);idx=rng.integers(0,len(ga),(B,len(ga)))
    totaln=ga.n.to_numpy()[idx].sum(axis=1)
    delta=(gb.singleton.to_numpy()-ga.singleton.to_numpy())[idx].sum(axis=1)/totaln
    wholedelta=(gb.whole_study.to_numpy()-ga.whole_study.to_numpy())[idx].mean(axis=1)
    contrasts={"study_max_minus_pooled_singleton_rate":{"estimate":b["singleton_rate"]-a["singleton_rate"],"lo":float(np.quantile(delta,.025)),"hi":float(np.quantile(delta,.975))},
               "study_max_minus_pooled_whole_study_coverage":{"estimate":b["whole_study_coverage"]-a["whole_study_coverage"],"lo":float(np.quantile(wholedelta,.025)),"hi":float(np.quantile(wholedelta,.975))}}
    result={"audit":json.loads((ROOT/"results/data_audit.json").read_text()),"primary_random_forest_metrics":perf[perf.model=="random_forest"].to_dict("records"),
            "primary_external_sets":sets[(sets.model=="random_forest")&(sets.regime=="external")&(sets.alpha==.10)].to_dict("records"),"contrasts":contrasts,
            "bootstrap":{"replicates":B,"unit":"source study","conditional_on_fitted_predictions":True,"interval":"percentile 95%"}}
    def clean(x):
        if isinstance(x,dict): return {k:clean(v) for k,v in x.items()}
        if isinstance(x,list): return [clean(v) for v in x]
        if isinstance(x,float) and not np.isfinite(x): return None
        return x
    (ROOT/"results/statistics.json").write_text(json.dumps(clean(result),indent=2,allow_nan=False),encoding="utf-8")
    print(perf[perf.model=="random_forest"].to_string(index=False))
    print(sets[(sets.model=="random_forest")&(sets.regime=="external")&(sets.alpha==.10)][["method","row_coverage","study_coverage","whole_study_coverage","singleton_rate","singleton_error"]].to_string(index=False))
    print(json.dumps(contrasts,indent=2))

if __name__=="__main__":main()
