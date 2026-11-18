"""Fixed-model study-held-out benchmark and split conformal classification."""
from pathlib import Path
import os
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")
import json
import hashlib
import platform
import sys
import time
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.impute import SimpleImputer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold, StratifiedKFold, GroupShuffleSplit, train_test_split
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261118
NUM = ["size_nm","dose_ug_ml","time_h"]
CAT = ["serum","surface","shape","synthesis","species","cell","disease","medium","assay"]
ALPHAS = [0.05,0.10,0.20]
METHODS = ["pooled","one_per_study","study_max"]

def conformal_quantile(scores, alpha):
    scores = np.asarray(scores, dtype=float)
    k = int(np.ceil((len(scores)+1)*(1-alpha)))
    return np.inf if k>len(scores) else float(np.sort(scores)[k-1])

def prediction_set(p, q):
    p = np.asarray(p)
    return (p<=q).astype(np.int8) + 2*((1-p)<=q).astype(np.int8)

def calibrate(y,p,groups,seed):
    scores = np.where(np.asarray(y)==1,1-p,p)
    d = pd.DataFrame({"s":scores,"g":np.asarray(groups)})
    rng = np.random.default_rng(seed)
    one = np.array([rng.choice(x.s.to_numpy()) for _,x in d.groupby("g",sort=True)])
    units = {"pooled":scores,"one_per_study":one,"study_max":d.groupby("g",sort=True).s.max().to_numpy()}
    return {(method,alpha):(conformal_quantile(s,alpha),len(s)) for method,s in units.items() for alpha in ALPHAS}

def estimator(name, seed, no_assay=False):
    cat = [c for c in CAT if c!="assay" or not no_assay]
    pre = ColumnTransformer([
        ("numeric",make_pipeline(SimpleImputer(strategy="median"),FunctionTransformer(np.log1p),StandardScaler()),NUM),
        ("categorical",OneHotEncoder(handle_unknown="ignore",sparse_output=False),cat)])
    model = {
        "prevalence": lambda:DummyClassifier(strategy="prior"),
        "logistic":lambda:LogisticRegression(C=1,max_iter=2000,random_state=seed),
        "random_forest":lambda:RandomForestClassifier(n_estimators=300,min_samples_leaf=3,max_features=1.0,n_jobs=4,random_state=seed),
        "hist_gradient_boosting":lambda:HistGradientBoostingClassifier(max_iter=150,learning_rate=.05,max_leaf_nodes=15,l2_regularization=1,early_stopping=False,random_state=seed)
    }[name]()
    return make_pipeline(pre,model)

def split_fit_cal(train, grouped, seed):
    if grouped:
        a,b = next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=seed).split(train,groups=train.study))
    else:
        a,b = train_test_split(np.arange(len(train)),test_size=.25,stratify=train.y,random_state=seed)
    return train.iloc[a],train.iloc[b]

def main():
    start=time.time()
    outdir=ROOT/"results/checkpoints"
    outdir.mkdir(parents=True,exist_ok=True)
    data=pd.read_csv(ROOT/"data/processed/canonical.csv")
    dev=data[data.cohort=="development"].reset_index(drop=True)
    ext=data[data.cohort=="external"].reset_index(drop=True)
    # Fail rather than reuse a result after code or data changes.
    fingerprint=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/"data/processed/canonical.csv").read_bytes()).hexdigest()
    stamp=outdir/"fingerprint.txt"
    if stamp.exists() and stamp.read_text()!=fingerprint:
        raise RuntimeError("Analysis changed; use a new checkpoint directory or explicitly archive previous outputs")
    stamp.write_text(fingerprint)
    tasks=[]
    for regime in ["row","study"]:
        for repeat in range(3):
            cv=(StratifiedKFold(n_splits=5,shuffle=True,random_state=SEED+repeat) if regime=="row"
                else GroupKFold(n_splits=5,shuffle=True,random_state=SEED+repeat))
            for fold,(tr,te) in enumerate(cv.split(dev,dev.y,groups=dev.study if regime=="study" else None)):
                fit,cal=split_fit_cal(dev.iloc[tr],regime=="study",SEED+repeat*100+fold)
                tasks.append((regime,repeat,fold,fit,cal,dev.iloc[te],["prevalence","logistic","random_forest","hist_gradient_boosting"]))
    for repeat in range(5):
        fit,cal=split_fit_cal(dev,True,SEED+repeat)
        tasks.append(("external",repeat,0,fit,cal,ext,["prevalence","logistic","random_forest","hist_gradient_boosting"]))
    # Planned source-quality and assay ablations plus a grouped permutation control.
    for regime in ["study_no_assay","study_exclude_flagged","study_permuted"]:
        d=dev[~dev.publication_id.isin([13,84,87])] if "exclude_flagged" in regime else dev
        for fold,(tr,te) in enumerate(GroupKFold(5,shuffle=True,random_state=SEED).split(d,groups=d.study)):
            fit,cal=split_fit_cal(d.iloc[tr],True,SEED+fold)
            tasks.append((regime,0,fold,fit,cal,d.iloc[te],["random_forest"]))
    for regime in ["external_no_assay","external_exclude_flagged"]:
        d=dev[~dev.publication_id.isin([13,84,87])] if "exclude_flagged" in regime else dev
        fit,cal=split_fit_cal(d,True,SEED)
        tasks.append((regime,0,0,fit,cal,ext,["random_forest"]))
    thresholds=[]; memberships=[]; checks=[]; files=[]
    for regime,repeat,fold,fit,cal,test,models in tasks:
        assert not(set(fit.row_id)&set(cal.row_id) or set(fit.row_id)&set(test.row_id) or set(cal.row_id)&set(test.row_id))
        grouped=regime!="row"
        overlaps={"fit_cal":len(set(fit.study)&set(cal.study)),"fit_test":len(set(fit.study)&set(test.study)),"cal_test":len(set(cal.study)&set(test.study))}
        if grouped: assert max(overlaps.values())==0
        checks.append({"regime":regime,"repeat":repeat,"fold":fold,**overlaps,
                       "fit_n":len(fit),"cal_n":len(cal),"test_n":len(test),
                       "fit_studies":fit.study.nunique(),"cal_studies":cal.study.nunique(),"test_studies":test.study.nunique()})
        for role,d in [("fit",fit),("calibration",cal),("test",test)]:
            m=d[["row_id","study"]].copy();m["role"]=role;m["regime"]=regime;m["repeat"]=repeat;m["fold"]=fold
            memberships.append(m)
        for name in models:
            file=outdir/f"{regime}_{repeat}_{fold}_{name}.csv"
            qfile=file.with_suffix(".json")
            if file.exists() and qfile.exists():
                thresholds.extend(json.loads(qfile.read_text()));files.append(file);continue
            seed=SEED+repeat*100+fold
            model=estimator(name,seed,no_assay="no_assay" in regime)
            y=fit.y.to_numpy()
            if "permuted" in regime: y=np.random.default_rng(seed).permutation(y)
            with threadpool_limits(limits=4):
                model.fit(fit,y)
                pc=model.predict_proba(cal)[:,1]
                pt=model.predict_proba(test)[:,1]
            quantiles=calibrate(cal.y,pc,cal.study,seed)
            out=test[["row_id","study","publication_id","y","size_nm","overlap_profile"]].copy()
            out["p"]=pt;out["model"]=name;out["regime"]=regime;out["repeat"]=repeat;out["fold"]=fold
            local=[]
            for (method,alpha),(q,n) in quantiles.items():
                out[f"set_{method}_{alpha:.2f}"]=prediction_set(pt,q)
                local.append({"model":name,"regime":regime,"repeat":repeat,"fold":fold,"method":method,"alpha":alpha,
                              "q":q if np.isfinite(q) else None,"n_calibration_units":n})
            out.to_csv(file,index=False);qfile.write_text(json.dumps(local,indent=2))
            thresholds.extend(local);files.append(file)
            print(f"{regime} repeat={repeat} fold={fold} {name}: fit={len(fit)}, calibration={len(cal)}, test={len(test)}",flush=True)
    pd.concat([pd.read_csv(f) for f in files],ignore_index=True).to_csv(ROOT/"results/predictions.csv",index=False)
    pd.concat(memberships,ignore_index=True).to_csv(ROOT/"results/split_membership.csv",index=False)
    pd.DataFrame(checks).to_csv(ROOT/"results/split_checks.csv",index=False)
    pd.DataFrame(thresholds).to_csv(ROOT/"results/calibration_thresholds.csv",index=False)
    meta={"python":sys.version,"platform":platform.platform(),"numpy":np.__version__,"pandas":pd.__version__,"sklearn":sklearn.__version__,
          "seed":SEED,"analysis_fingerprint":fingerprint,"elapsed_seconds":time.time()-start,"fit_tasks":len(files),
          "sap_sha256":hashlib.sha256((ROOT/"reports/STATISTICAL_ANALYSIS_PLAN.md").read_bytes()).hexdigest()}
    (ROOT/"results/execution.json").write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2),flush=True)

if __name__=="__main__":main()
