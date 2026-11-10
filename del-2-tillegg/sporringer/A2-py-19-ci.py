# A2/19 Wilson-intervaller for nøkkeltallene
import math, sys
sys.stdout.reconfigure(encoding='utf-8')
def wilson(k,n,z=1.959963985):
    if n==0: return (float('nan'),)*3
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return 100*p, 100*(c-h), 100*(c+h)
def line(lab,k,n):
    p,lo,hi=wilson(k,n)
    print(f"{lab:<52} {k:>6}/{n:<6} {p:5.1f} %  [{lo:.1f}–{hi:.1f}]")
print("== ANDEL MED «Åpnet etter» ==")
line("kohort 2023-09-01..2024-12-31", 3734, 5165)
line("hele korpuset, alle aapninger", 10009, 13644)
line("2019-2022 (retensjonstynnet, L1)", 496, 810)
line("2023", 2165, 3058); line("2024", 2793, 3860); line("2025", 2767, 3695); line("2026 t.o.m. 24.08", 1776, 2208)
print()
print("== UTFALL (innstilt) ETTER GRUNNLAG ==")
line("oppbud, as-of 24.08.2026", 2772, 3734)
line("ingen felt, as-of 24.08.2026", 1125, 1431)
line("oppbud, 730d fast vindu", 2000, 2745)
line("ingen felt, 730d fast vindu", 812, 1027)
def diff(k1,n1,k2,n2,lab):
    p1,p2=k1/n1,k2/n2; d=p2-p1
    se=math.sqrt(p1*(1-p1)/n1+p2*(1-p2)/n2)
    print(f"{lab:<52} {100*d:+5.1f} pp  [{100*(d-1.96*se):+.1f}–{100*(d+1.96*se):+.1f}]")
diff(2772,3734,1125,1431,"differanse (ingen felt − oppbud), as-of")
diff(2000,2745, 812,1027,"differanse (ingen felt − oppbud), 730d")
print()
print("== PROSESSTEST: fristdag -> aapning <= 7 dager ==")
line("oppbud", 3356, 3734)
line("ingen felt  (TAK paa parser-tap)", 3, 1431)
line("ingen felt, <= 2 dager", 1, 1431)
line("ingen felt, 0 dager", 0, 1431)
print()
print("== EKSTERN FORANKRING ==")
o,bg,tv=43.6,25.7,30.7
print(f"  2021-rapport tabell 4 panel C: oppbud {o} %, begjaering {bg} %, tvangsavvikling {tv} %")
print(f"  konkurs-only oppbudsandel     = {o}/({o}+{bg}) = {100*o/(o+bg):.1f} %")
print(f"  vaar 2019-2022 feltandel      = 496/810 = {100*496/810:.1f} %   (differanse {100*496/810-100*o/(o+bg):+.1f} pp)")
