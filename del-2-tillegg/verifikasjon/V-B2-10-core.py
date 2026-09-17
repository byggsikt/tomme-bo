import pandas as pd, numpy as np, math, sys, json
H="../data/"
df=pd.read_csv(H+"V-B2-03-extract.csv",dtype={"orgnr":str,"tingrett":str,"bransje":str})
for c in ["opened","innstilt","avsluttet","gk_siste","rev_siste","stiftet","nyreg","forste_any","fristdag","vt_siste"]:
    df[c]=pd.to_datetime(df[c],errors="coerce")
BOOLC=["oppbud","rev_siste_fratradt","vt_24m","vt_12m","vt_regn","vt_foretak","dl_utgaar_12m","rev_utgaar_12m"]
for c in BOOLC:
    if c in df.columns:
        df[c]=df[c].map({"t":True,"f":False,True:True,False:False})
print("BOOL parse:",{c:df[c].dropna().unique().tolist() for c in BOOLC})
print("rows",len(df),"unique orgnr",df.orgnr.nunique())
print("utfall",df.utfall.value_counts().to_dict())
# outcome flags
df["y_asof"]=(df.utfall=="innstilt").astype(int)
df["full"]=df.opened<=pd.Timestamp("2024-08-24")
df["y730"]=((df.d_innstilt.notna())&(df.d_innstilt<=730)).astype(int)
df["avsl730"]=(((df.d_innstilt.isna())|(df.d_innstilt>730))&(df.d_avsluttet.notna())&(df.d_avsluttet<=730)).astype(int)
df["open730"]=(1-df.y730-df.avsl730)
f=df[df.full]
print("FULL n",len(f),"y730",int(f.y730.sum()),"avsl730",int(f.avsl730.sum()),"open730",int(f.open730.sum()))
print("asof all: n",len(df),"innstilt",int(df.y_asof.sum()))
# --- unit sanity in selected accounts
print("acc units:",df.acc_unit.fillna("<blank>").value_counts(dropna=False).to_dict())
print("has pre-open acc:",int(df.acc_fy.notna().sum()),"  no acc row at all:",int((df.acc_n_rows==0).sum()),
      "  has rows but none pre-open:",int(((df.acc_n_rows>0)&(df.acc_fy.isna())).sum()))
# --- KEY ADVERSARIAL TEST: are the "no pre-opening account" estates a source-coverage gap?
na=df[df.acc_fy.isna()]
print("\n=== NO PRE-OPENING ACCOUNT: n =",len(na))
print("  of which HAVE a Godkjent-årsregnskap announcement before opening (i.e. they DID file):",int((na.gk_n>0).sum()))
print("  gk_n==0 (never announced an approved account):",int((na.gk_n==0).sum()))
print("  innstilt as-of:",int(na.y_asof.sum()),"/",len(na))
sub=na[na.gk_n>0]; sub2=na[na.gk_n==0]
print("  innstilt as-of | filed-but-missing-numbers:",int(sub.y_asof.sum()),"/",len(sub),
      " | never filed:",int(sub2.y_asof.sum()),"/",len(sub2))
# compare to companies WITH account
ha=df[df.acc_fy.notna()]
print("  innstilt as-of | with account:",int(ha.y_asof.sum()),"/",len(ha))
df.to_pickle(H+"V-B2-core.pkl")
