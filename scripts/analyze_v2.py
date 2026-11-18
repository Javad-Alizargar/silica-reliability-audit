"""Exploratory extension: conditional coverage, domain novelty and learning curves."""
from pathlib import Path
import json,hashlib,time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score,average_precision_score,roc_curve,precision_recall_curve
from threadpoolctl import threadpool_limits
from analyze import estimator,NUM,CAT,SEED
from reliability import METHODS,thresholds,sets,summary

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/v2';OUT.mkdir(exist_ok=True)
ALPHAS=[.01,.02,.05,.10,.15,.20,.25,.30]

def clean(obj):
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,list):return [clean(v) for v in obj]
    if isinstance(obj,(np.integer,)):return int(obj)
    if isinstance(obj,(float,np.floating)) and not np.isfinite(obj):return None
    return obj

def prob(model,d):
    probabilities=model.predict_proba(d);classes=model[-1].classes_
    return probabilities[:,list(classes).index(1)] if 1 in classes else np.zeros(len(d))

def domain(fit,query):
    fn=np.log1p(fit[NUM].to_numpy(float));qn=np.log1p(query[NUM].to_numpy(float))
    lower=fn.min(axis=0);upper=fn.max(axis=0);width=np.maximum(upper-lower,1e-12)
    fc=[];qc=[];unknown=np.zeros(len(query),int)
    for col in CAT:
        keys={v:i for i,v in enumerate(sorted(fit[col].astype(str).unique()))}
        fc.append(fit[col].astype(str).map(keys).to_numpy(int))
        z=query[col].astype(str).map(keys).fillna(-1).to_numpy(int);qc.append(z);unknown+=(z<0)
    distance=[]
    for start in range(0,len(query),128):
        end=min(start+128,len(query))
        d=np.zeros((end-start,len(fit)),float)
        for j in range(3):d+=np.minimum(np.abs(qn[start:end,j,None]-fn[None,:,j])/width[j],1)
        for j in range(9):d+=(qc[j][start:end,None]!=fc[j][None,:])
        distance.extend(d.min(axis=1)/12)
    return pd.DataFrame({'distance':distance,'unknown_categories':unknown,'outside_numeric':((qn<lower)|(qn>upper)).sum(axis=1)},index=query.index)

def point(d):
    y=d.y.to_numpy();p=d.p.to_numpy();binary=p>=.5
    return {'n':len(d),'studies':d.study.nunique(),'positive':int(y.sum()),
            'auc':roc_auc_score(y,p) if len(np.unique(y))==2 else np.nan,
            'average_precision':average_precision_score(y,p) if y.sum() else np.nan,
            'brier':float(np.mean((p-y)**2)),'error':float(np.mean(binary!=y)),
            'sensitivity':float(binary[y==1].mean()) if y.sum() else np.nan,
            'specificity':float((~binary[y==0]).mean()) if (y==0).sum() else np.nan}

def main():
    started=time.time();data=pd.read_csv(ROOT/'data/processed/canonical.csv');lookup=data.set_index('row_id',drop=False)
    membership=pd.read_csv(ROOT/'results/split_membership.csv');orig=pd.read_csv(ROOT/'results/predictions.csv')
    fingerprint=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/'scripts/reliability.py').read_bytes()+(ROOT/'data/processed/canonical.csv').read_bytes()).hexdigest()
    stamp=OUT/'checkpoints/fingerprint.txt'
    if stamp.exists():assert stamp.read_text()==fingerprint,'Extension changed; archive checkpoint directory before rerunning'
    stamp.write_text(fingerprint)
    all_test=[];all_cal=[];all_q=[];recovery=[];fullfit=None;fullcal=None;fulltest=None
    for (regime,fold),member in membership[(membership['repeat']==0)&membership.regime.isin(['row','study','external'])].groupby(['regime','fold'],sort=True):
        fit=lookup.loc[member.loc[member.role=='fit','row_id']].copy().reset_index(drop=True)
        cal=lookup.loc[member.loc[member.role=='calibration','row_id']].copy().reset_index(drop=True)
        test=lookup.loc[member.loc[member.role=='test','row_id']].copy().reset_index(drop=True)
        file=OUT/'checkpoints'/f'{regime}_{fold}'
        if file.with_suffix('.test.csv').exists():
            test=pd.read_csv(file.with_suffix('.test.csv'));cal=pd.read_csv(file.with_suffix('.cal.csv'))
            local=json.loads(file.with_suffix('.json').read_text())
        else:
            model=estimator('random_forest',SEED+fold)
            with threadpool_limits(limits=4):model.fit(fit,fit.y);cal['p']=prob(model,cal);test['p']=prob(model,test)
            dc=domain(fit,cal);dt=domain(fit,test)
            cuts=np.quantile(dc.distance,[.5,.75,.9])
            for target,diag in [(cal,dc),(test,dt)]:
                for c in diag:target[c]=diag[c].to_numpy()
                target['distance_bin']=np.searchsorted(cuts,target.distance,side='left')
                target['regime']=regime;target['fold']=fold
            local=[]
            for method in METHODS:
                for alpha in ALPHAS:
                    q=thresholds(cal,method,alpha,SEED+fold)
                    test[f'set_{method}_{alpha:.2f}']=sets(test.p,q)
                    local.append({'regime':regime,'fold':int(fold),'method':method,'alpha':alpha,'q0':q[0],'q1':q[1],
                                  'calibration_rows':len(cal),'calibration_sources':cal.study.nunique(),
                                  'distance_q50':cuts[0],'distance_q75':cuts[1],'distance_q90':cuts[2]})
            test.to_csv(file.with_suffix('.test.csv'),index=False);cal.to_csv(file.with_suffix('.cal.csv'),index=False)
            file.with_suffix('.json').write_text(json.dumps(clean(local),indent=2))
        previous=orig[(orig.regime==regime)&(orig.model=='random_forest')&(orig['repeat']==0)&(orig.fold==fold)].set_index('row_id')
        diff=float(np.max(np.abs(test.p.to_numpy()-previous.loc[test.row_id,'p'].to_numpy())))
        assert diff<1e-12,(regime,fold,diff)
        recovery.append({'regime':regime,'fold':fold,'max_probability_difference':diff})
        all_test.append(test);all_cal.append(cal);all_q.extend(local)
        if regime=='external':fullfit,fullcal,fulltest=fit,cal,test
        print(f'Recovered {regime} fold {fold}; max difference {diff:.3g}',flush=True)
    test=pd.concat(all_test,ignore_index=True);cal=pd.concat(all_cal,ignore_index=True)
    test.to_csv(OUT/'predictions.csv',index=False);cal.to_csv(OUT/'calibration_predictions.csv',index=False)
    pd.DataFrame(all_q).to_csv(OUT/'thresholds.csv',index=False);pd.DataFrame(recovery).to_csv(OUT/'recovery_checks.csv',index=False)
    evaluations=[];classifiers=[];curves=[];risk=[];conditional=[];source_rows=[]
    for regime,d in test.groupby('regime'):
        classifiers.append({'regime':regime,**point(d)})
        fpr,tpr,t=roc_curve(d.y,d.p);curves.extend({'regime':regime,'curve':'ROC','x':x,'y':y,'threshold':t0} for x,y,t0 in zip(fpr,tpr,t))
        precision,recall,t=precision_recall_curve(d.y,d.p);curves.extend({'regime':regime,'curve':'PR','x':x,'y':y,'threshold':None} for x,y in zip(recall,precision))
        for threshold in np.r_[np.arange(.5,.951,.05),.975,.99]:
            accept=np.maximum(d.p,1-d.p)>=threshold;wrong=(d.p>=.5)!=d.y
            risk.append({'regime':regime,'threshold':float(threshold),'accepted_rate':float(accept.mean()),'accepted_n':int(accept.sum()),
                         'error_rate':float(wrong[accept].mean()) if accept.any() else np.nan,
                         'false_negative_fraction':float(((d.p<.5)&(d.y==1)&accept).sum()/(d.y==1).sum())})
        for method in METHODS:
            for alpha in ALPHAS:evaluations.append({'regime':regime,'method':method,'alpha':alpha,**summary(d,d[f'set_{method}_{alpha:.2f}'])})
        d=d.copy();d['size_group']=np.where(d.size_nm<=100,'<=100 nm','>100 nm')
        d['dose_group']=pd.cut(d.dose_ug_ml,[-np.inf,10,100,np.inf],labels=['<=10','10-100','>100']).astype(str)
        d['time_group']=np.where(d.time_h<=24,'<=24 h','>24 h');d['unknown_group']=np.where(d.unknown_categories>0,'Unseen category','All categories seen')
        for variable in ['assay','serum','species','size_group','dose_group','time_group','distance_bin','unknown_group']:
            for level,g in d.groupby(variable,observed=True):
                for method in METHODS:
                    conditional.append({'regime':regime,'variable':variable,'level':str(level),'method':method,**point(g),**summary(g,g[f'set_{method}_0.10']),
                                        'main_display_eligible':len(g)>=30 and g.study.nunique()>=5})
        for source,g in d.groupby('study'):
            for method in METHODS:source_rows.append({'regime':regime,'study':source,'publication_id':int(g.publication_id.iloc[0]),'method':method,
                                                     'mean_distance':g.distance.mean(),**point(g),**summary(g,g[f'set_{method}_0.10'])})
    pd.DataFrame(evaluations).to_csv(OUT/'calibration_performance.csv',index=False)
    pd.DataFrame(classifiers).to_csv(OUT/'point_metrics.csv',index=False)
    pd.DataFrame(curves).to_csv(OUT/'discrimination_curves.csv',index=False)
    pd.DataFrame(risk).to_csv(OUT/'confidence_risk_curves.csv',index=False)
    pd.DataFrame(conditional).to_csv(OUT/'conditional_metrics.csv',index=False)
    pd.DataFrame(source_rows).to_csv(OUT/'source_metrics.csv',index=False)
    # Source-bootstrap contrasts condition on the fixed, recovered primary predictions.
    bootrows=[]
    for regime,d in test.groupby('regime'):
        groups=[g for _,g in d.groupby('study',sort=True)];rng=np.random.default_rng(SEED)
        index=rng.integers(0,len(groups),(2000,len(groups)))
        for method in METHODS:
            per=[]
            for g in groups:
                c=g[f'set_{method}_0.10'].to_numpy(int);y=g.y.to_numpy(int);hit=(c&(1<<y))>0;single=np.isin(c,[1,2]);wrong=single&~hit
                per.append([len(g),int((y==0).sum()),int((y==1).sum()),int((hit&(y==0)).sum()),int((hit&(y==1)).sum()),int(single.sum()),int(wrong.sum())])
            totals=np.asarray(per)[index].sum(axis=1)
            for metric,num,den in [('coverage_negative',3,1),('coverage_positive',4,2),('singleton_rate',5,0),('singleton_error',6,5)]:
                values=np.divide(totals[:,num],totals[:,den],out=np.full(2000,np.nan),where=totals[:,den]>0)
                bootrows.append({'regime':regime,'method':method,'metric':metric,'lo':float(np.nanquantile(values,.025)),'hi':float(np.nanquantile(values,.975))})
    pd.DataFrame(bootrows).to_csv(OUT/'conditional_intervals.csv',index=False)
    # A study-level learning curve with fixed calibration and external evaluation.
    learning=[];train_sources=np.array(sorted(fullfit.study.unique()))
    for repeat in range(5):
        order=np.random.default_rng(SEED+1000+repeat).permutation(train_sources)
        for n_sources in [10,20,40,60,86]:
            file=OUT/'checkpoints'/f'learning_{repeat}_{n_sources}.json'
            if file.exists():learning.extend(json.loads(file.read_text()));continue
            subset=fullfit[fullfit.study.isin(order[:n_sources])]
            if n_sources==86:
                pc=fullcal.p.to_numpy();pt=fulltest.p.to_numpy()
            else:
                model=estimator('random_forest',SEED)
                with threadpool_limits(limits=4):model.fit(subset,subset.y);pc=prob(model,fullcal);pt=prob(model,fulltest)
            c=fullcal.copy();c['p']=pc;d=fulltest.copy();d['p']=pt;local=[]
            for method in METHODS:
                q=thresholds(c,method,.1,SEED)
                local.append({'repeat':repeat,'fitting_sources':n_sources,'fitting_rows':len(subset),'method':method,**point(d),**summary(d,sets(pt,q))})
            file.write_text(json.dumps(clean(local),indent=2));learning.extend(local)
            print(f'Learning curve repeat {repeat}: {n_sources} sources',flush=True)
    pd.DataFrame(learning).to_csv(OUT/'learning_curve.csv',index=False)
    # Source/context composition and frozen external example for the public audit tool.
    shifts=[]
    for variable in CAT:
        dev=data[data.cohort=='development'][variable].value_counts(normalize=True)
        ext=data[data.cohort=='external'][variable].value_counts(normalize=True)
        levels=dev.index.union(ext.index)
        for level in levels:shifts.append({'variable':variable,'level':level,'development_fraction':dev.get(level,0),'external_fraction':ext.get(level,0)})
    pd.DataFrame(shifts).to_csv(OUT/'context_shift.csv',index=False)
    demo=[]
    for role,d in [('calibration',fullcal),('evaluation',fulltest)]:
        x=d[['row_id','study','y','p','size_nm','dose_ug_ml','time_h','assay','serum']].copy();x['role']=role;demo.append(x)
    pd.concat(demo).to_csv(OUT/'audit_example.csv',index=False)
    meta={'fingerprint':fingerprint,'original_primary_recovered':len(recovery),'additional_learning_fits':20,
          'max_recovery_difference':max(x['max_probability_difference'] for x in recovery),
          'elapsed_seconds':time.time()-started,'plan_sha256':hashlib.sha256((ROOT/'reports/v2/ANALYSIS_PLAN_V2.md').read_bytes()).hexdigest(),
          'status':'exploratory post-hoc extension; no evaluation-set tuning'}
    (OUT/'execution.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))

if __name__=='__main__':main()
