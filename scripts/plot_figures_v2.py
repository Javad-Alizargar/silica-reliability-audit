"""Five six-panel scientific figures. Plot saved results; never refit models."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'manuscript/v2/figures'
SRC=OUT/'source_data'
SRC.mkdir(parents=True,exist_ok=True)
R=ROOT/'results/v2'
REG=['row','study','external']; RL=['Random rows','Held-out studies','External']
METHODS=['pooled','one_per_study','study_max','label_conditional']
ML=['Pooled rows','One per study','Study maximum','Label conditional']
C=['#0072B2','#D55E00','#009E73','#8C56A0']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.5,'axes.titlesize':9.5,
 'axes.labelsize':8.5,'legend.fontsize':7,'xtick.labelsize':7.5,'ytick.labelsize':7.5,
 'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
manifest=[]
def source(df,name): df.to_csv(SRC/(name+'.csv'),index=False)
def panel(ax,letter,title):
    short={'Novel categories relative to fitting data':'Unseen experimental categories',
      'Random-forest precision and recall':'Random-forest precision–recall',
      'Coverage of cytotoxic observations':'Cytotoxic-class coverage',
      'Coverage of non-cytotoxic observations':'Non-cytotoxic-class coverage',
      'Entire held-out sources covered':'Whole-source coverage',
      'Decisiveness on held-out sources':'Singletons on held-out sources',
      'Distance does not order error reliably':'Error by distance bin',
      'Context subgroups (≥5 sources)':'Assay and serum subgroups',
      'Unseen-category error contrast':'Error with unseen categories',
      'Probability error by source count':'Learning: probability error',
      'Conservative decisiveness is variable':'Conservative singleton outputs',
      'Class coverage across fitting budgets':'Cytotoxic-class coverage',
      'Five fitting/calibration partitions':'Five fitting/calibration splits',
      'Subsets and feature sensitivity':'Subsets and feature ablations'}
    import textwrap
    ax.set_title(letter+'  '+textwrap.fill(short.get(title,title),34),loc='left',fontweight='bold',pad=8)
def canvas():
    fig,axs=plt.subplots(3,2,figsize=(7.35,8.25),layout='constrained')
    return fig,axs.ravel()
def legend(fig,labels=RL,colors=C,ncol=3):
    fig.legend(handles=[Line2D([],[],color=c,marker='o',lw=1,label=l) for c,l in zip(colors,labels)],
      loc='outside lower center',ncol=ncol,frameon=False)
def save(fig,name):
    for ext in ['pdf','svg','png']:fig.savefig(OUT/(name+'.'+ext),dpi=600,facecolor='white')
    fig.savefig(OUT/(name+'_preview.png'),dpi=150,facecolor='white')
    plt.close(fig);manifest.append({'figure':name,'panels':'A-F','dpi':600,'source_directory':'figures/source_data'})
def main():
    data=pd.read_csv(ROOT/'data/processed/canonical.csv');pred=pd.read_csv(R/'predictions.csv')
    perf=pd.read_csv(ROOT/'results/model_performance.csv'); cp=pd.read_csv(R/'calibration_performance.csv')
    cond=pd.read_csv(R/'conditional_metrics.csv'); sm=pd.read_csv(R/'source_metrics.csv')
    pm=pd.read_csv(R/'point_metrics.csv');ci=pd.read_csv(R/'conditional_intervals.csv')
    fig,a=canvas()
    tab=data.groupby(['cohort','study']).size().reset_index(name='n')
    for j,co in enumerate(['development','external']):
        x=tab[tab.cohort==co].sort_values('n',ascending=False)
        a[0].plot(np.arange(1,len(x)+1),x.n,color=C[j],label=f'{co.capitalize()} ({len(x)} sources)')
    a[0].set(xlabel='Source rank',ylabel='Observations per source',yscale='log');a[0].legend(frameon=False)
    panel(a[0],'A','Unequal source contributions');source(tab,'F1A_source_counts')
    parts=[]
    for j,co in enumerate(['development','external']):
        x=np.sort(data.loc[data.cohort==co,'dose_ug_ml']);y=np.arange(1,len(x)+1)/len(x)
        a[1].plot(x,y,color=C[j]);parts.append(pd.DataFrame({'cohort':co,'dose_ug_ml':x,'ecdf':y}))
    a[1].axvline(10000,c='.5',ls=':',lw=1);a[1].set(xscale='log',xlabel='Reported concentration (µg/mL)',ylabel='Cumulative fraction')
    panel(a[1],'B','Exposure distributions');source(pd.concat(parts),'F1B_dose_ecdf')
    tab=data.groupby(['cohort','study']).y.agg(['mean','size']).reset_index();rng=np.random.default_rng(421)
    for j,co in enumerate(['development','external']):
        t=tab[tab.cohort==co];a[2].scatter(j+rng.uniform(-.18,.18,len(t)),t['mean'],s=8+np.sqrt(t['size'])*2,color=C[j],alpha=.5)
        a[2].plot([j-.23,j+.23],[t['mean'].mean()]*2,c='black',lw=2)
    a[2].set(xticks=[0,1],xticklabels=['Development','External'],ylabel='Cytotoxic fraction per source',ylim=(-.04,1.04))
    panel(a[2],'C','Label heterogeneity');source(tab,'F1C_source_prevalence')
    shift=pd.read_csv(R/'context_shift.csv');shift['abs_difference']=(shift.development_fraction-shift.external_fraction).abs()
    tab=(shift.groupby('variable').abs_difference.sum()/2).sort_values().reset_index(name='total_variation')
    a[3].barh(tab.variable,tab.total_variation,color=C[0]);a[3].set(xlabel='Total variation between cohorts',xlim=(0,1))
    panel(a[3],'D','Categorical context shift');source(tab,'F1D_context_shift')
    tab=pred.assign(unseen=lambda x:x.unknown_categories>0).groupby('regime').agg(n=('y','size'),unseen=('unseen','sum')).reindex(REG).reset_index()
    tab['fraction']=tab.unseen/tab.n;a[4].bar(RL,tab.fraction,color=C[:3]);a[4].set(ylabel='Fraction with an unseen category',ylim=(0,.65))
    for i,r in tab.iterrows():a[4].text(i,r.fraction+.02,f'{r.unseen:,}/{r.n:,}',ha='center',fontsize=7)
    panel(a[4],'E','Novel categories relative to fitting data');source(tab,'F1E_unseen_categories')
    a[5].axis('off');panel(a[5],'F','Fixed external evaluation split')
    tab=pd.DataFrame({'role':['Fit','Calibrate','Evaluate'],'rows':[2660,1456,905],'sources':[86,29,26]})
    for i,r in tab.iterrows():
        y=.72-i*.28;a[5].add_patch(FancyBboxPatch((.08,y),.82,.19,boxstyle='round,pad=.02',fc='#EDF3F6',ec='#829AA5',transform=a[5].transAxes))
        a[5].text(.49,y+.095,f'{r.role}: {r.rows:,} rows / {r.sources} sources',ha='center',va='center',transform=a[5].transAxes,fontsize=8)
        if i<2:a[5].annotate('',xy=(.49,y-.06),xytext=(.49,y-.01),xycoords='axes fraction',arrowprops=dict(arrowstyle='->',color='.4'))
    a[5].text(.49,.04,'Disjoint sources in all three partitions',ha='center',transform=a[5].transAxes,fontsize=7.5)
    source(tab,'F1F_external_split');save(fig,'Figure_1_data_and_context')

    fig,a=canvas();models=['prevalence','logistic','random_forest','hist_gradient_boosting']
    labels=['Prevalence','Logistic','Random forest','Histogram boosting']
    for ax,metric,letter,title in [(a[0],'auc','A','Discrimination'),(a[1],'brier','B','Probability error')]:
        tab=perf[perf.regime.isin(REG)]
        for j,reg in enumerate(REG):
            t=tab[tab.regime==reg].set_index('model').loc[models];v=t[metric].to_numpy()
            err=np.vstack([np.maximum(0,v-t[metric+'_lo']),np.maximum(0,t[metric+'_hi']-v)])
            ax.errorbar(v,np.arange(4)+(j-1)*.2,xerr=err,fmt='o',ms=3,capsize=2,c=C[j])
        ax.set(yticks=range(4),yticklabels=labels,xlabel='AUROC' if metric=='auc' else 'Brier score');ax.invert_yaxis()
        panel(ax,letter,title);source(tab,'F2'+letter+'_models')
    tab=pd.read_csv(R/'discrimination_curves.csv');tab=tab[tab.curve=='PR']
    for j,reg in enumerate(REG):
        t=tab[tab.regime==reg];a[2].plot(t.x,t.y,c=C[j],lw=1.2)
    a[2].set(xlabel='Recall',ylabel='Precision',xlim=(0,1),ylim=(0,1));panel(a[2],'C','Random-forest precision and recall');source(tab,'F2C_precision_recall')
    parts=[]
    for j,reg in enumerate(REG):
        t=pred[pred.regime==reg].copy();t['bin']=pd.cut(t.p,np.linspace(0,1,9),include_lowest=True)
        b=t.groupby('bin',observed=True).agg(predicted=('p','mean'),observed=('y','mean'),n=('y','size')).reset_index(drop=True);b['regime']=reg
        a[3].plot(b.predicted,b.observed,'o-',c=C[j],ms=3);parts.append(b)
    a[3].plot([0,1],[0,1],c='.6',ls='--',lw=1);a[3].set(xlabel='Mean predicted probability',ylabel='Observed cytotoxic fraction',xlim=(0,1),ylim=(0,1))
    panel(a[3],'D','Probability reliability');source(pd.concat(parts),'F2D_reliability')
    for j,reg in enumerate(REG):
        t=pm[pm.regime==reg].iloc[0];a[4].plot([0,1],[t.sensitivity,t.specificity],'o-',c=C[j],ms=4)
    a[4].set(xticks=[0,1],xticklabels=['Sensitivity','Specificity'],ylabel='Fraction at probability cutoff 0.5',ylim=(0,1.05))
    panel(a[4],'E','Asymmetric classification');source(pm,'F2E_classification')
    tab=sm[sm.method=='pooled']
    for j,reg in enumerate(REG):
        t=tab[tab.regime==reg];a[5].scatter(j+rng.uniform(-.18,.18,len(t)),t.brier,s=10,c=C[j],alpha=.5)
        a[5].plot([j-.2,j+.2],[t.brier.mean()]*2,c='black',lw=2)
    a[5].set(xticks=range(3),xticklabels=['Rows','Studies','External'],ylabel='Source Brier score',ylim=(-.02,1.02))
    panel(a[5],'F','Error varies between sources');source(tab,'F2F_source_brier');legend(fig);save(fig,'Figure_2_validation')

    fig,a=canvas();tab=cp[np.isclose(cp.alpha,.1)]
    for ax,metric,letter,title in [(a[0],'coverage_positive','A','Coverage of cytotoxic observations'),(a[1],'coverage_negative','B','Coverage of non-cytotoxic observations')]:
        for j,m in enumerate(METHODS):
            t=tab[tab.method==m].set_index('regime').loc[REG];q=ci[(ci.method==m)&(ci.metric==metric)].set_index('regime').loc[REG]
            v=t[metric].to_numpy();ax.errorbar(np.arange(3)+(j-1.5)*.17,v,yerr=np.vstack([np.maximum(0,v-q.lo),np.maximum(0,q.hi-v)]),fmt='o',ms=3,c=C[j],capsize=2)
        ax.axhline(.9,c='.6',ls='--',lw=1);ax.set(xticks=range(3),xticklabels=['Rows','Studies','External'],ylabel='Class coverage',ylim=(.25,1.04))
        panel(ax,letter,title);source(tab.merge(ci[ci.metric==metric],on=['regime','method']),f'F3{letter}_class_coverage')
    for ax,metric,letter,title in [(a[2],'whole_coverage','C','Entire held-out sources covered'),(a[3],'singleton_rate','D','Decisiveness on held-out sources')]:
        t=cp[cp.regime=='study']
        for j,m in enumerate(METHODS):
            x=t[t.method==m];ax.plot(x.alpha,x[metric],'o-',c=C[j],ms=3)
        if metric=='whole_coverage':ax.plot([.01,.3],[.99,.7],c='.6',ls='--',lw=1)
        ax.set(xlabel='Nominal miscoverage α',ylabel='Whole-source coverage' if metric=='whole_coverage' else 'Singleton fraction',ylim=(-.02,1.04))
        panel(ax,letter,title);source(t,f'F3{letter}_alpha_curve')
    tab=cp[cp.regime=='external']
    for j,m in enumerate(METHODS):
        t=tab[tab.method==m];a[4].plot(t.singleton_rate,t.singleton_error,'o-',c=C[j],ms=2.5)
        t=t[np.isclose(t.alpha,.1)];a[4].scatter(t.singleton_rate,t.singleton_error,s=40,facecolors='none',edgecolors=C[j],linewidth=1.5)
    a[4].set(xlabel='Singleton fraction',ylabel='Observed singleton error',ylim=(-.01,.25),xlim=(-.02,1.02));panel(a[4],'E','External risk and decisiveness');source(tab,'F3E_external_risk')
    tab=pd.read_csv(R/'confidence_risk_curves.csv')
    for j,reg in enumerate(REG):
        t=tab[tab.regime==reg];a[5].plot(t.accepted_rate,t.error_rate,'o-',c=C[j],ms=3,label=RL[j])
    a[5].set(xlabel='Fraction accepted by confidence cutoff',ylabel='Observed error among accepted',ylim=(-.02,.5));a[5].legend(frameon=False)
    panel(a[5],'F','Confidence-threshold comparator');source(tab,'F3F_confidence_risk')
    legend(fig,ML,C,2);save(fig,'Figure_3_calibration_and_abstention')

    fig,a=canvas();parts=[]
    for j,reg in enumerate(REG):
        t=np.sort(pred.loc[pred.regime==reg,'distance']);y=np.arange(1,len(t)+1)/len(t);a[0].plot(t,y,c=C[j]);parts.append(pd.DataFrame({'regime':reg,'distance':t,'ecdf':y}))
    a[0].set(xlabel='Distance to nearest fitting observation',ylabel='Cumulative fraction');panel(a[0],'A','Distance from the fitting set');source(pd.concat(parts),'F4A_distance')
    tab=cond[(cond.variable=='distance_bin')&(cond.method=='pooled')]
    for j,reg in enumerate(REG):
        t=tab[tab.regime==reg].sort_values('level');a[1].plot(range(len(t)),t.brier,'o-',c=C[j],ms=4)
    a[1].set(xticks=range(4),xticklabels=['≤50th','50–75th','75–90th','>90th'],xlabel='Calibration-distance percentile bin',ylabel='Brier score',ylim=(0,.4))
    panel(a[1],'B','Distance does not order error reliably');source(tab,'F4B_distance_bins')
    tab=pd.read_csv(R/'error_detection.csv').set_index('regime').loc[REG].reset_index()
    for j,(col,lab) in enumerate([('distance_error_auc','Mixed-feature distance'),('uncertainty_error_auc','Probability uncertainty')]):
        a[2].plot(range(3),tab[col],'o-',c=[C[3],C[0]][j],label=lab)
    a[2].axhline(.5,c='.6',ls='--',lw=1);a[2].set(xticks=range(3),xticklabels=['Rows','Studies','External'],ylabel='AUROC for detecting prediction errors',ylim=(.35,.95));a[2].legend(frameon=False)
    panel(a[2],'C','Error-detection diagnostics');source(tab,'F4C_error_detection')
    tab=cond[(cond.regime=='external')&(cond.method=='pooled')&(cond.main_display_eligible)&cond.variable.isin(['assay','serum'])].copy()
    tab['label']=tab.variable+': '+tab.level.astype(str)+' (n='+tab.n.astype(str)+')';tab=tab.sort_values(['variable','level'])
    a[3].scatter(tab.brier,range(len(tab)),c=C[2],s=22);a[3].set(yticks=range(len(tab)),yticklabels=tab.label,xlabel='External Brier score');a[3].invert_yaxis()
    panel(a[3],'D','Context subgroups (≥5 sources)');source(tab,'F4D_subgroups')
    tab=sm[(sm.regime=='study')&sm.method.isin(['pooled','study_max'])]
    for j,m in enumerate(['pooled','study_max']):
        t=tab[tab.method==m];a[4].scatter(t.n,t.row_coverage,s=13,c=[C[0],C[2]][j],alpha=.55,label=['Pooled rows','Study maximum'][j])
    a[4].set(xscale='log',xlabel='Observations in held-out source',ylabel='Within-source coverage',ylim=(-.04,1.04));a[4].legend(frameon=False)
    panel(a[4],'E','Coverage across source sizes');source(tab,'F4E_source_size')
    tab=pd.read_csv(R/'contrasts.csv');tab=tab[tab.contrast=='unknown_minus_known_brier'].set_index('regime').loc[REG].reset_index()
    a[5].errorbar(tab.estimate,range(3),xerr=np.vstack([tab.estimate-tab.lo,tab.hi-tab.estimate]),fmt='o',c=C[3],capsize=3)
    a[5].axvline(0,c='.6',ls='--',lw=1);a[5].set(yticks=range(3),yticklabels=RL,xlabel='Brier difference: unseen − known');a[5].invert_yaxis()
    panel(a[5],'F','Unseen-category error contrast');source(tab,'F4F_unseen_contrasts');legend(fig);save(fig,'Figure_4_applicability_diagnostics')

    fig,a=canvas();learn=pd.read_csv(R/'learning_curve.csv')
    for ax,metric,letter,title in [(a[0],'auc','A','Learning from more sources'),(a[1],'brier','B','Probability error by source count')]:
        t=learn[learn.method=='pooled'];q=t.groupby('fitting_sources')[metric].agg(['min','median','max']).reset_index()
        for _,g in t.groupby('repeat'):ax.plot(g.fitting_sources,g[metric],c=C[0],alpha=.2,lw=.8)
        ax.errorbar(q.fitting_sources,q['median'],yerr=np.vstack([q['median']-q['min'],q['max']-q['median']]),fmt='o-',c=C[0],capsize=3,ms=4)
        ax.set(xlabel='Fitting sources (calibration fixed at 29)',ylabel='External AUROC' if metric=='auc' else 'External Brier score')
        panel(ax,letter,title);source(t,f'F5{letter}_learning')
    tab=learn[learn.method=='study_max']
    for _,t in tab.groupby('repeat'):a[2].plot(t.fitting_sources,t.singleton_rate,'o-',c=C[2],alpha=.5,ms=3)
    a[2].set(xlabel='Fitting sources',ylabel='Study-maximum singleton fraction',ylim=(-.01,.55));panel(a[2],'C','Conservative decisiveness is variable');source(tab,'F5C_learning_singletons')
    parts=[]
    for j,m in enumerate(['pooled','study_max','label_conditional']):
        t=learn[learn.method==m];q=t.groupby('fitting_sources').coverage_positive.agg(['min','median','max']).reset_index();q['method']=m;parts.append(q)
        a[3].plot(q.fitting_sources,q['median'],'o-',c=C[METHODS.index(m)],ms=3,label=ML[METHODS.index(m)])
    a[3].axhline(.9,c='.6',ls='--',lw=1);a[3].set(xlabel='Fitting sources',ylabel='Median cytotoxic-class coverage',ylim=(.45,1.04));a[3].legend(frameon=False)
    panel(a[3],'D','Class coverage across fitting budgets');source(pd.concat(parts),'F5D_learning_coverage')
    sen=pd.read_csv(ROOT/'results/sensitivity.csv');tab=sen[sen.subset=='all']
    for j,m in enumerate(METHODS[:3]):
        t=tab[tab.method==m];a[4].scatter(t.singleton_rate,t.singleton_error,c=C[j],s=25,marker=['o','s','^'][j],label=ML[j])
    a[4].set(xlabel='External singleton fraction',ylabel='Observed singleton error',xlim=(0,.7),ylim=(-.01,.2));a[4].legend(frameon=False)
    panel(a[4],'E','Five fitting/calibration partitions');source(tab,'F5E_split_sensitivity')
    sub=sen[(sen.repeat==0)&(sen.method=='pooled')].set_index('subset').loc[['all','literature_only','size_le100','unmatched_profiles']]
    vals=sub.auc.to_list()+perf[(perf.model=='random_forest')&perf.regime.isin(['external_no_assay','external_exclude_flagged'])].set_index('regime').loc[['external_no_assay','external_exclude_flagged'],'auc'].to_list()
    labels=['All observations','Literature only','Size ≤100 nm','Unmatched profiles','Without assay','Original dose flags excluded']
    tab=pd.DataFrame({'analysis':labels,'auc':vals});a[5].scatter(tab.auc,range(6),c=C[0],s=24);a[5].axvline(vals[0],c='.6',ls=':',lw=1)
    a[5].set(yticks=range(6),yticklabels=labels,xlabel='External AUROC',xlim=(.8,.93));a[5].invert_yaxis();panel(a[5],'F','Subsets and feature sensitivity')
    source(tab,'F5F_sensitivity');save(fig,'Figure_5_learning_and_robustness')
    (OUT.parent/'figure_manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Five figures, 30 panels: vector PDF/SVG, 600 dpi PNG and panel-level CSV.')

if __name__=='__main__':main()
