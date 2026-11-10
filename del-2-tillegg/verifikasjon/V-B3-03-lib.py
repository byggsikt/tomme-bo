# V-B3 shared library: data load + statistics, written independently for the adversarial check.
import io, os, math, json
import numpy as np
import pandas as pd
from scipy import stats

DIR = r"../data"
ASOF = pd.Timestamp("2026-08-24")

COLS = ["orgnr","opened","utfall","innstilt","avsluttet","bransje","n_bransje","tingrett","n_tingrett",
        "n_apningsrader","oppbud","fiscal_year","source_name","amount_unit","currency",
        "total_assets","current_assets","equity","liabilities","current_liabilities",
        "operating_revenue","operating_result","annual_result","payroll_expenses","employee_count",
        "n_acc_before","min_fy_before","n_acc_any","max_fy_any","stiftet"]

def load():
    df = pd.read_csv(os.path.join(DIR,"V-B3-01-kohort.txt"), sep="|", header=None, names=COLS,
                     dtype={"orgnr":str}, keep_default_na=False, na_values=[""])
    kl = pd.read_csv(os.path.join(DIR,"V-B3-02-kohort-klassifisert.tsv"), sep="\t",
                     dtype={"orgnr":str}, keep_default_na=False, na_values=[""])
    kl = kl[["orgnr","nace","kilde","bygg_F","bygg_U"]]
    df = df.merge(kl, on="orgnr", how="left", validate="1:1")
    for c in ["opened","innstilt","avsluttet","stiftet"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["oppbud"] = df["oppbud"].map({"t":True,"f":False})
    for c in ["total_assets","current_assets","equity","liabilities","current_liabilities",
              "operating_revenue","operating_result","annual_result","payroll_expenses","employee_count",
              "fiscal_year","n_acc_before","n_acc_any","max_fy_any","min_fy_before"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # currency conversion for the two non-NOK rows (same treatment as B3; banding is insensitive)
    rate = {"EUR":11.5,"USD":10.5}
    fx = df["currency"].map(rate).fillna(1.0)
    for c in ["total_assets","current_assets","equity","liabilities","current_liabilities","operating_revenue"]:
        df[c] = df[c]*fx
    df["bygg"] = df["bygg_U"].fillna(0).astype(int)==1
    df["har_regnskap"] = df["fiscal_year"].notna()
    df["innstilt_flag"] = df["utfall"].eq("innstilt")
    df["dager_innstilt"]  = (df["innstilt"]  - df["opened"]).dt.days
    df["dager_avsluttet"] = (df["avsluttet"] - df["opened"]).dt.days
    # competing-risks time: innstilling wins (study outcome rule); otherwise ordinary closure; else censored
    t = np.where(df["utfall"].eq("innstilt"), df["dager_innstilt"],
        np.where(df["utfall"].eq("avsluttet"), df["dager_avsluttet"], (ASOF-df["opened"]).dt.days))
    ev = np.where(df["utfall"].eq("innstilt"), 1, np.where(df["utfall"].eq("avsluttet"), 2, 0))
    df["t"] = t; df["ev"] = ev
    df["full730"] = df["opened"] <= pd.Timestamp("2024-08-24")
    df["innstilt730"] = df["innstilt_flag"] & (df["dager_innstilt"]<=730)
    df["alder_ar"] = (df["opened"]-df["stiftet"]).dt.days/365.25
    df["gap_ar"] = df["opened"].dt.year - df["fiscal_year"]
    # asset / revenue bands
    def band_ta(r):
        if not r["har_regnskap"]: return "ingen regnskap"
        v = r["total_assets"]
        if pd.isna(v): return "ingen regnskap"
        if v < 1e6: return "<1 MNOK"
        if v < 5e6: return "1-5 MNOK"
        return ">=5 MNOK"
    def band_ta7(r):
        if not r["har_regnskap"] or pd.isna(r["total_assets"]): return "ingen regnskap"
        v = r["total_assets"]
        if v == 0: return "=0"
        if v < 0.5e6: return "<0,5"
        if v < 1e6: return "0,5-1"
        if v < 5e6: return "1-5"
        if v < 20e6: return "5-20"
        return ">=20"
    def band_rev(r):
        if not r["har_regnskap"]: return "ingen regnskap"
        v = r["operating_revenue"]
        if pd.isna(v): return "mangler"
        if v < 1e6: return "<1 MNOK"
        if v < 5e6: return "1-5 MNOK"
        if v < 20e6: return "5-20 MNOK"
        return ">=20 MNOK"
    df["band_ta"]  = df.apply(band_ta, axis=1)
    df["band_ta7"] = df.apply(band_ta7, axis=1)
    df["band_rev"] = df.apply(band_rev, axis=1)
    return df

# ---------- statistics ----------
def wilson(k,n,z=1.959963984540054):
    if n==0: return (float("nan"),float("nan"))
    p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (c-h, c+h)

def newcombe(k1,n1,k2,n2):
    """Newcombe method 10 CI for p1-p2."""
    l1,u1=wilson(k1,n1); l2,u2=wilson(k2,n2)
    p1=k1/n1; p2=k2/n2
    lo=(p1-p2)-math.sqrt((p1-l1)**2+(u2-p2)**2)
    hi=(p1-p2)+math.sqrt((u1-p1)**2+(p2-l2)**2)
    return lo,hi

def pct(k,n): return 100.0*k/n if n else float("nan")

def prop_row(name,k1,n1,k2,n2):
    lo,hi=newcombe(k1,n1,k2,n2)
    return dict(navn=name, b_k=int(k1), b_n=int(n1), b_p=round(pct(k1,n1),1),
                o_k=int(k2), o_n=int(n2), o_p=round(pct(k2,n2),1),
                diff_pp=round(pct(k1,n1)-pct(k2,n2),1),
                lo_pp=round(100*lo,1), hi_pp=round(100*hi,1))

def aj_cif(t, ev, horizon=730):
    """Aalen-Johansen CIF for cause 1 with cause 2 competing, evaluated at `horizon`."""
    t=np.asarray(t,float); ev=np.asarray(ev,int)
    order=np.argsort(t); t=t[order]; ev=ev[order]
    n=len(t); S=1.0; cif=0.0; at_risk=n; i=0
    while i<n:
        ti=t[i]; j=i
        d1=d2=dc=0
        while j<n and t[j]==ti:
            if ev[j]==1: d1+=1
            elif ev[j]==2: d2+=1
            else: dc+=1
            j+=1
        if ti<=horizon and at_risk>0:
            cif += S*(d1/at_risk)
            S   *= (1-(d1+d2)/at_risk)
        at_risk -= (j-i); i=j
        if ti>horizon: break
    return cif

def aj_boot(t,ev,horizon=730,B=600,seed=20260912):
    rng=np.random.default_rng(seed); t=np.asarray(t,float); ev=np.asarray(ev,int); n=len(t)
    out=np.empty(B)
    for b in range(B):
        idx=rng.integers(0,n,n); out[b]=aj_cif(t[idx],ev[idx],horizon)
    return float(np.percentile(out,2.5)), float(np.percentile(out,97.5))

def mh_or(tab):
    """tab: list of (a,b,c,d) = (bygg event, bygg no-event, other event, other no-event) per stratum."""
    num=den=0.0
    for a,b,c,d in tab:
        n=a+b+c+d
        if n==0: continue
        num+=a*d/n; den+=b*c/n
    return num/den if den>0 else float("nan")

def standardise(df, strat, group_col="bygg", outcome="innstilt730"):
    """Direct standardisation: bygg rates weighted by the OTHER group's stratum distribution."""
    o = df[~df[group_col]]; b = df[df[group_col]]
    w = o[strat].value_counts(normalize=True)
    rates = b.groupby(strat)[outcome].mean()
    common = [s for s in w.index if s in rates.index]
    wt = w.loc[common]/w.loc[common].sum()
    std = float((rates.loc[common]*wt).sum())
    return std, float(o[outcome].mean()), [(int(b[(b[strat]==s)][outcome].sum()), int((b[strat]==s).sum()),
                                            int(o[(o[strat]==s)][outcome].sum()), int((o[strat]==s).sum())) for s in common]

# ---------- logistic regression (IRLS) ----------
def logit_fit(X, y, ridge=1e-8, maxit=200, tol=1e-10):
    X=np.asarray(X,float); y=np.asarray(y,float)
    n,p=X.shape; beta=np.zeros(p)
    for _ in range(maxit):
        eta=X@beta; eta=np.clip(eta,-30,30); mu=1/(1+np.exp(-eta))
        W=np.maximum(mu*(1-mu),1e-10)
        z=eta+(y-mu)/W
        A=X.T@(X*W[:,None]) + ridge*np.eye(p)
        bnew=np.linalg.solve(A, X.T@(W*z))
        if np.max(np.abs(bnew-beta))<tol: beta=bnew; break
        beta=bnew
    eta=np.clip(X@beta,-30,30); mu=1/(1+np.exp(-eta)); W=np.maximum(mu*(1-mu),1e-10)
    cov=np.linalg.inv(X.T@(X*W[:,None])+ridge*np.eye(p))
    return beta, cov

def loglik(X,y,beta):
    eta=np.clip(np.asarray(X,float)@beta,-30,30)
    return float(np.sum(y*eta-np.log1p(np.exp(eta))))

def design(df, cols_cat, cols_num=(), byggcol="bygg"):
    """Returns X (with intercept, bygg first), y, names."""
    parts=[np.ones(len(df)), df[byggcol].astype(float).values]
    names=["const","bygg"]
    for c in cols_cat:
        levels=sorted(df[c].astype(str).unique())
        for lv in levels[1:]:
            parts.append((df[c].astype(str)==lv).astype(float).values); names.append(f"{c}={lv}")
    for c in cols_num:
        parts.append(df[c].astype(float).values); names.append(c)
    return np.column_stack(parts), names

def marginal_rd(X, y, beta, bygg_idx=1):
    X1=X.copy(); X1[:,bygg_idx]=1.0
    X0=X.copy(); X0[:,bygg_idx]=0.0
    p1=1/(1+np.exp(-np.clip(X1@beta,-30,30)))
    p0=1/(1+np.exp(-np.clip(X0@beta,-30,30)))
    return float(p1.mean()-p0.mean())

def model(df, cols_cat, cols_num=(), y="innstilt730", B=300, seed=20260912, boot=True):
    X,names=design(df,cols_cat,cols_num)
    yv=df[y].astype(float).values
    beta,cov=logit_fit(X,yv)
    se=math.sqrt(cov[1,1]); orv=math.exp(beta[1])
    lo,hi=math.exp(beta[1]-1.959964*se), math.exp(beta[1]+1.959964*se)
    z=beta[1]/se; p=2*(1-stats.norm.cdf(abs(z)))
    rd=marginal_rd(X,yv,beta)
    rdlo=rdhi=float("nan")
    if boot:
        rng=np.random.default_rng(seed); n=len(yv); out=[]
        for _ in range(B):
            idx=rng.integers(0,n,n)
            try:
                bb,_=logit_fit(X[idx],yv[idx])
                out.append(marginal_rd(X[idx],yv[idx],bb))
            except Exception: pass
        if out: rdlo,rdhi=float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
    return dict(OR=orv, OR_lo=lo, OR_hi=hi, p=p, RD_pp=100*rd, RD_lo_pp=100*rdlo, RD_hi_pp=100*rdhi,
                beta=beta, names=names, ll=loglik(X,yv,beta), k=X.shape[1])
