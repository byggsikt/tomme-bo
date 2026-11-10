# B1-00: validate B1_lib against the study's frozen extract (READ ONLY).
# Must reproduce TALLJOURNAL I1 (24 m CIF 74.82 / 70.54 / 76.23, CI 73.60-75.99),
# I1b (12 m 63.18/57.11/65.17; 18 m 71.89/66.87/73.54), I2 (Gray z = -5.671, chi2 = 32.157),
# I2b (RD -5.70 pp [-8.56; -2.83]), I3 (CIF medians bygg 267 [245-302], other 205 [196-217]).
import json, sys, datetime as dt
import numpy as np
sys.path.insert(0, r"../data")
from B1_lib import AJ, gray_test, H12, H18, H24, Z

FROZEN = r"../../del-1-hovedstudien/data/_kohort-rader-arbeidskopi.json"
END = dt.date(2026, 8, 24)
rows = json.load(open(FROZEN, encoding="utf-8"))

t = []; cause = []; bygg = []
for r in rows:
    op = dt.date.fromisoformat(r["aapning"])
    oppf = (END - op).days
    rand = r["dager_til_innstilling"] is not None and r["dager_til_innstilling"] < 0
    if rand:
        tt, cc = oppf, 0                      # primary boundary rule "sensurert"
    elif r["innstilling"]:
        tt, cc = r["dager_til_innstilling"], 1
    elif r["avslutning"]:
        tt, cc = r["dager_til_avslutning"], 2
    else:
        tt, cc = oppf, 0
    t.append(max(0, tt)); cause.append(cc); bygg.append(r["bygg_utforende"] is True)
t = np.array(t); cause = np.array(cause); bygg = np.array(bygg)
print("frozen rows", len(rows), "bygg", bygg.sum(), "innstilt", (cause == 1).sum(), "avsluttet", (cause == 2).sum(), "open", (cause == 0).sum())

out = {}
for name, m in [("alle", np.ones(len(t), bool)), ("bygg", bygg), ("ovrige", ~bygg)]:
    aj = AJ(t[m], cause[m])
    line = []
    for h in (H12, H18, H24):
        lo, hi, se = aj.ci(h)
        line.append(f"{h}d: {100*aj.F1(h):.2f} [{100*lo:.2f}-{100*hi:.2f}] rm {aj.at_risk(h)}")
    q = aj.quantile(0.5); qlo, qhi = aj.quantile_ci(0.5)
    print(f"{name:7s} n={m.sum():5d}  " + " | ".join(line) + f" | median {q} [{qlo}-{qhi}]")
    out[name] = aj

U, V, z, p = gray_test(t[bygg], cause[bygg], t[~bygg], cause[~bygg])
print(f"Gray bygg vs ovrige: U={U:.3f} V={V:.3f} z={z:.3f} chi2={z*z:.3f} p={p:.3e}")
for h in (H12, H18, H24):
    fB, fO = out["bygg"].F1(h), out["ovrige"].F1(h)
    se = np.sqrt(out["bygg"].var(h) + out["ovrige"].var(h))
    print(f"RD {h}d: {100*(fB-fO):.2f} pp [{100*(fB-fO-Z*se):.2f}; {100*(fB-fO+Z*se):.2f}]")
