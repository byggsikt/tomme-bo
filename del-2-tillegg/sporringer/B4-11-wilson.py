import math
def wilson(k,n,z=1.959963985):
    if n==0: return (float('nan'),float('nan'),float('nan'))
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (100*p,100*(c-h),100*(c+h))
def row(lbl,k,n):
    p,lo,hi=wilson(k,n)
    print(f"{lbl:<48} {k:>6} / {n:<6} = {p:5.1f} %  [{lo:.1f}; {hi:.1f}]")

print("=== 1. DELETION after outcome (as-of 24.08.2026) ===")
row("Slettet etter innstilling",3881,3897)
row("Slettet etter ordinaer avslutning",917,917)
row("Slettet blant fortsatt aapne bo",0,351)
row("Sletting samme dag som innstilling",3050,3881)
row("Sletting samme dag som avslutning",713,917)
row("Sletting <=30 d etter innstilling",3050+824,3881)
row("Sletting <=30 d etter avslutning",713+199,917)
print()
print("=== 2. Announcements that could say anything about money ===")
row("Bo med skiftesamlingskunngjoring",6,5165)
row("Bo med ny fordringsfrist",1,5165)
row("Bo med fordringshavermote",0,5165)
row("Bo med ny bostyrer",64,5165)
row("Bo med fortsettelse (gjenopptakelse)",7,5165)
row("Innstilte bo som senere ble avsluttet",4,3897)
print()
print("=== 3. Outcome given a signal (decided estates only) ===")
row("Innstilt | ingen signal",3853,3853+898)
row("Innstilt | skiftesamlingskunngjoring",3,3+3)
row("Innstilt | ny bostyrer",41,41+16)
print()
print("=== 4. Revenue band x outcome, AS-OF 24.08.2026 (share innstilt of decided) ===")
band=[("<1 MNOK",1146,115,39),("1-5 MNOK",1302,294,80),("5-20 MNOK",595,313,102),(">20 MNOK",158,128,101),
      ("ingen omsetningstall",419,40,20),("ingen regnskap",277,27,9)]
tot_i=tot_a=tot_o=0
for lbl,i,a,o in band:
    row(f"innstilt | {lbl}",i,i+a); tot_i+=i; tot_a+=a; tot_o+=o
row("innstilt | ALLE",tot_i,tot_i+tot_a)
print("kontroll:",tot_i,tot_a,tot_o,tot_i+tot_a+tot_o)
print()
print("=== 5. Revenue band x outcome, FIXED 730-DAY WINDOW (opened <= 2024-08-24) ===")
b730=[("<1 MNOK",946,828,85,33),("1-5 MNOK",1228,940,233,55),("5-20 MNOK",729,430,214,85),
      (">20 MNOK",280,100,89,91),("ingen omsetningstall",348,303,29,16),("ingen regnskap",241,211,20,10)]
T=I=A=O=0
for lbl,n,i,a,o in b730:
    row(f"innstilt innen 730 d | {lbl}",i,n); T+=n; I+=i; A+=a; O+=o
row("innstilt innen 730 d | ALLE",I,T)
print("kontroll:",T,I,A,O,I+A+O)
print()
print("=== 6. payroll coverage ===")
row("annual_account-rader med payroll_expenses (hele basen)",2702+59+24,652642)
row("annual_account-rader med payroll_expenses (kohorten)",0,5190)
row("brreg_ansatte-dekning, innstilte bo",15,3897)
row("brreg_ansatte-dekning, fortsatt aapne bo",349,351)
row("omsetningstall finnes (kohort)",4373,5165)
