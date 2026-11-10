# V-B3: is B3's bootstrap CI for the marginal risk difference stable at the reps it used?
# M0's marginal RD has a closed form (crude risk difference), so the bootstrap can be graded.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,"V-B3-03-lib.py"),encoding="utf-8").read())
df = load(); S = df[df.full730].copy()
kb=int(S[S.bygg].innstilt730.sum()); nb=int(S.bygg.sum()); ko=int(S[~S.bygg].innstilt730.sum()); no=int((~S.bygg).sum())
pb, po = kb/nb, ko/no
nc = newcombe(kb,nb,ko,no)
se = math.sqrt(pb*(1-pb)/nb + po*(1-po)/no)
wald = (100*((pb-po)-1.96*se), 100*((pb-po)+1.96*se))
rng_rd = S.bygg.values.astype(bool); yv = S.innstilt730.values.astype(bool)
def boot(B, seed):
    rng=np.random.default_rng(seed); n=len(yv); out=np.empty(B)
    for i in range(B):
        ix=rng.integers(0,n,n); b=rng_rd[ix]; y=yv[ix]
        out[i]=y[b].mean()-y[~b].mean()
    return round(100*float(np.percentile(out,2.5)),1), round(100*float(np.percentile(out,97.5)),1)
T=dict(punkt=round(100*(pb-po),1),
       newcombe=[round(100*nc[0],1),round(100*nc[1],1)],
       wald=[round(wald[0],1),round(wald[1],1)],
       boot_B150=[list(boot(150,s)) for s in (1,2,3,4,5)],
       boot_B300=[list(boot(300,s)) for s in (11,12,13,14,15)],
       boot_B20000=list(boot(20000,99)),
       B3_hovedrapport_M0=[-8.9,-2.6], B3_07_fil_M0=[-9.8,-2.7])
json.dump(T, open(os.path.join(DIR,"V-B3-10-bootstabilitet.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(T, indent=1, ensure_ascii=False))
