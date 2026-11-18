"""Publication plots from audited observations and saved predictions only."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"manuscript/figures"
SRC=OUT/"source_data"
OUT.mkdir(exist_ok=True);SRC.mkdir(exist_ok=True)
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.titlesize":10,"axes.labelsize":9,
                     "legend.fontsize":8,"xtick.labelsize":8,"ytick.labelsize":8,"axes.spines.top":False,
                     "axes.spines.right":False,"svg.fonttype":"none","pdf.fonttype":42})
C=["#0072B2","#D55E00","#009E73"]
REG=["row","study","external"]
RL=["Random rows","Held-out studies","External cohort"]
METHODS=["pooled","one_per_study","study_max"]
ML=["Pooled rows","One row per study","Study maximum"]
MODELS=["prevalence","logistic","random_forest","hist_gradient_boosting"]
MODEL_LABELS=["Prevalence","Logistic","Random forest","Histogram boosting"]

def panel(ax,label,title):
    ax.set_title(f"{label}  {title}",loc="left",fontweight="bold",pad=10)

def save(fig,name):
    for ext in ["png","pdf","svg"]:fig.savefig(OUT/f"{name}.{ext}",dpi=600,facecolor="white",bbox_inches="tight")
    fig.savefig(OUT/f"{name}_preview.png",dpi=140,facecolor="white",bbox_inches="tight")
    plt.close(fig)

def source(df,name):df.to_csv(SRC/f"{name}.csv",index=False)

def main():
    data=pd.read_csv(ROOT/"data/processed/canonical.csv")
    pred=pd.read_csv(ROOT/"results/predictions.csv")
    perf=pd.read_csv(ROOT/"results/model_performance.csv")
    sets=pd.read_csv(ROOT/"results/set_performance.csv")
    fig,axs=plt.subplots(2,2,figsize=(7.25,5.8),layout="constrained")
    a=axs[0,0];tab=data.groupby(["cohort","study"]).size().reset_index(name="observations")
    for j,co in enumerate(["development","external"]):
        x=tab[tab.cohort==co].sort_values("observations",ascending=False)
        a.plot(np.arange(1,len(x)+1),x.observations,marker=".",ms=3,color=C[j],label=f"{co.capitalize()} ({len(x)} sources)")
    a.set(yscale="log",xlabel="Source rank by sample count",ylabel="Observations per source");a.legend(frameon=False)
    panel(a,"A","Unequal contributions");source(tab,"F1A_source_sizes")
    a=axs[0,1];parts=[]
    for j,co in enumerate(["development","external"]):
        x=np.sort(data.loc[data.cohort==co,"dose_ug_ml"]);y=np.arange(1,len(x)+1)/len(x)
        a.plot(x,y,color=C[j],label=co.capitalize());parts.append(pd.DataFrame({"cohort":co,"dose_ug_ml":x,"ecdf":y}))
    a.axvline(10000,color=".5",ls=":",lw=1);a.text(13000,.28,"Audit flag",rotation=90,fontsize=8,color=".4")
    a.set(xscale="log",xlabel="Reported concentration (µg/mL)",ylabel="Cumulative fraction");panel(a,"B","Exposure distributions")
    source(pd.concat(parts),"F1B_dose_ecdf")
    a=axs[1,0];tab=data.groupby(["cohort","study"]).y.agg(["mean","size"]).reset_index()
    rng=np.random.default_rng(123)
    for j,co in enumerate(["development","external"]):
        x=tab[tab.cohort==co];a.scatter(j+rng.uniform(-.18,.18,len(x)),x['mean'],s=10+np.sqrt(x['size'])*3,alpha=.6,color=C[j],edgecolors="white",linewidth=.4)
        a.plot([j-.2,j+.2],[x['mean'].mean()]*2,color="black",lw=2)
    a.set(xticks=[0,1],xticklabels=["Development","External"],ylabel="Cytotoxic fraction within source",ylim=(-.04,1.04))
    panel(a,"C","Study-level label heterogeneity");source(tab,"F1C_source_prevalence")
    a=axs[1,1];a.set_axis_off();panel(a,"D","Frozen external evaluation")
    split=pd.read_csv(ROOT/"results/split_checks.csv").query("regime == 'external' and repeat == 0").iloc[0]
    split_text=lambda role: f"{int(split[role+'_n']):,} rows / {int(split[role+'_studies'])} sources"
    boxes=[(.02,.59,.43,.23,"Fit\n"+split_text('fit')),(.54,.59,.44,.23,"Calibrate\n"+split_text('cal')),(.20,.15,.62,.25,"Evaluate externally\n"+split_text('test'))]
    for x,y,w,h,t in boxes:
        a.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.015",fc="#EDF3F6",ec="#8DA6B0",lw=.8,transform=a.transAxes))
        a.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=8,transform=a.transAxes)
    for x in [.24,.76]:a.annotate("",xy=(.51,.41),xytext=(x,.58),xycoords="axes fraction",arrowprops=dict(arrowstyle="->",color="#56666C"))
    a.text(.5,.02,"Source groups remain disjoint",ha="center",fontsize=8,transform=a.transAxes)
    source(pd.DataFrame([{"role":r,"rows":int(split[r+'_n']),"sources":int(split[r+'_studies'])} for r in ['fit','cal','test']]),"F1D_split")
    save(fig,"Figure_1_data_and_design")

    fig,axs=plt.subplots(2,2,figsize=(7.25,6.1),layout="constrained")
    for ax,metric,title,letter in [(axs[0,0],"auc","Discrimination","A"),(axs[0,1],"brier","Probability error","B")]:
        tab=perf[perf.regime.isin(REG)]
        for j,reg in enumerate(REG):
            x=tab[tab.regime==reg].set_index("model").loc[MODELS]
            vals=x[metric].to_numpy();lo=x[f"{metric}_lo"].to_numpy();hi=x[f"{metric}_hi"].to_numpy()
            ax.errorbar(vals,np.arange(4)+(j-1)*.19,xerr=np.vstack([np.maximum(0,vals-lo),np.maximum(0,hi-vals)]),fmt="o",ms=3.5,capsize=2,color=C[j],label=RL[j])
        ax.set(yticks=np.arange(4),yticklabels=MODEL_LABELS,xlabel="AUROC" if metric=="auc" else "Brier score")
        ax.invert_yaxis();panel(ax,letter,title);source(tab,"F2"+letter+"_model_metrics")
    fig.legend(handles=[Line2D([],[],color=c,marker='o',ls='none',label=t) for c,t in zip(C,RL)],loc="outside lower center",ncol=3,frameon=False,fontsize=8)
    a=axs[1,0];parts=[]
    for j,reg in enumerate(REG):
        d=pred[(pred.regime==reg)&(pred.model=="random_forest")&(pred.repeat==0)].copy()
        d["bin"]=pd.cut(d.p,np.linspace(0,1,9),include_lowest=True)
        b=d.groupby("bin",observed=True).agg(predicted=("p","mean"),observed=("y","mean"),n=("y","size")).reset_index(drop=True);b["regime"]=reg
        a.plot(b.predicted,b.observed,"o-",ms=3,color=C[j]);parts.append(b)
    a.plot([0,1],[0,1],ls="--",color=".6",lw=1);a.set(xlabel="Mean predicted probability",ylabel="Observed cytotoxic fraction",xlim=(0,1),ylim=(0,1))
    panel(a,"C","Random-forest reliability");source(pd.concat(parts),"F2C_reliability_bins")
    a=axs[1,1];parts=[]
    for j,reg in enumerate(REG):
        d=pred[(pred.regime==reg)&(pred.model=="random_forest")&(pred.repeat==0)].copy();d["loss"]=(d.p-d.y)**2
        b=d.groupby("study").loss.mean().reset_index();b["regime"]=reg
        a.scatter(j+rng.uniform(-.18,.18,len(b)),b.loss,s=12,color=C[j],alpha=.5)
        a.plot([j-.2,j+.2],[b.loss.mean()]*2,c="black",lw=2);parts.append(b)
    a.set(xticks=[0,1,2],xticklabels=["Rows","Studies","External"],ylabel="Mean Brier score per source",ylim=(-.02,1.02));panel(a,"D","Variation across sources")
    source(pd.concat(parts),"F2D_source_brier");save(fig,"Figure_2_validation")

    tab=sets[(sets.model=="random_forest")&(sets.regime.isin(REG))&(sets.alpha==.1)]
    fig,axs=plt.subplots(2,2,figsize=(7.25,5.8),layout="constrained")
    for ax,metric,title,letter in zip(axs.flat,["row_coverage","study_coverage","whole_study_coverage","singleton_rate"],["Row coverage","Study-balanced row coverage","Whole-study coverage","Single-label predictions"],"ABCD"):
        for j,method in enumerate(METHODS):
            x=tab[tab.method==method].set_index("regime").loc[REG];val=x[metric].to_numpy()
            lo=x[f"{metric}_lo"].to_numpy();hi=x[f"{metric}_hi"].to_numpy()
            if metric=="whole_study_coverage":lo[-1]=x.loc['external','whole_study_exact_lo'];hi[-1]=x.loc['external','whole_study_exact_hi']
            ax.errorbar(np.arange(3)+(j-1)*.2,val,yerr=np.vstack([np.maximum(0,val-lo),np.maximum(0,hi-val)]),fmt="o",capsize=2,ms=4,color=C[j],label=ML[j])
        if metric!="singleton_rate":ax.axhline(.9,color=".6",ls="--",lw=.8)
        ax.set(xticks=[0,1,2],xticklabels=["Rows","Studies","External"],ylim=(0,1.06),ylabel="Fraction")
        panel(ax,letter,title);source(tab,"F3"+letter+"_coverage")
    fig.legend(handles=[Line2D([],[],color=c,marker='o',ls='none',label=t) for c,t in zip(C,ML)],loc="outside lower center",ncol=3,frameon=False,fontsize=8)
    save(fig,"Figure_3_coverage_and_abstention")

    fig,axs=plt.subplots(2,2,figsize=(7.25,6.4),layout="constrained")
    sen=pd.read_csv(ROOT/"results/sensitivity.csv");t=sen[sen.subset=="all"]
    a=axs[0,0]
    for j,m in enumerate(METHODS):
        x=t[t.method==m];a.scatter(x.singleton_rate,x.singleton_error,s=32,c=C[j],label=ML[j],marker=["o","s","^"][j])
    a.set(xlabel="Fraction receiving one label",ylabel="Error fraction among singletons",xlim=(0,1),ylim=(-.01,max(.2,t.singleton_error.max()+.03)))
    a.legend(frameon=False,fontsize=7);panel(a,"A","Calibration split sensitivity");source(t,"F4A_repeat_risk")
    ps=pd.read_csv(ROOT/"results/per_study_sets.csv");ps=ps[(ps.regime=="external")&(ps.model=="random_forest")&(ps.alpha==.1)]
    mapping=data.drop_duplicates('study').set_index('study').publication_id
    for ax,col,title,letter in [(axs[0,1],"study_coverage","Coverage by external source","B"),(axs[1,1],"singleton_fraction","Singleton rate by source","D")]:
        z=ps.copy();z["singleton_fraction"]=z.singleton/z.n;z["id"]=z.study.map(mapping)
        piv=z.pivot(index="id",columns="method",values=col).reindex(columns=METHODS).sort_index()
        im=ax.imshow(piv.to_numpy(),aspect="auto",cmap="cividis",vmin=0,vmax=1)
        ax.set(xticks=range(3),xticklabels=["Pooled","One/study","Maximum"],yticks=np.arange(0,26,2),yticklabels=piv.index[::2],ylabel="Source ID")
        fig.colorbar(im,ax=ax,fraction=.045,pad=.02,label="Fraction")
        panel(ax,letter,title);source(piv.reset_index(),f"F4{letter}_source_matrix")
    a=axs[1,0];sub=sen[(sen.repeat==0)&(sen.method=="pooled")].set_index("subset").loc[["all","literature_only","size_le100","unmatched_profiles"]]
    vals=sub.auc.to_list()+perf[(perf.model=="random_forest")&perf.regime.isin(["external_no_assay","external_exclude_flagged"])].set_index("regime").loc[["external_no_assay","external_exclude_flagged"],"auc"].to_list()
    labels=["All observations","Literature only","Size ≤100 nm","Unmatched profiles","Without assay","Flagged sources removed"]
    a.scatter(vals,np.arange(6),c=C[0],s=28);a.axvline(vals[0],ls=":",c=".6");a.set(yticks=np.arange(6),yticklabels=labels,xlabel="External AUROC",xlim=(.70,1));a.invert_yaxis();panel(a,"C","Sensitivity analyses")
    source(pd.DataFrame({"analysis":labels,"auc":vals}),"F4C_sensitivity");save(fig,"Figure_4_external_robustness")
    manifest=[]
    for n in ["Figure_1_data_and_design","Figure_2_validation","Figure_3_coverage_and_abstention","Figure_4_external_robustness"]:
        manifest.append({"figure":n,"vector":[n+".svg",n+".pdf"],"raster":n+".png","dpi":600,"plot_script":"scripts/plot_figures.py","source_directory":"manuscript/figures/source_data"})
    (ROOT/"manuscript/figure_manifest.json").write_text(json.dumps(manifest,indent=2))
    print("Four figures exported as SVG, PDF, 600-dpi PNG; panel sources saved.")

if __name__=="__main__":main()
