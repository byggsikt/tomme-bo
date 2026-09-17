# V/09 Verifier: direct standardisation of the basis contrast (ingen_felt - oppbud) for balance-sheet size (and bygg), as-of and 730-day window.
import csv, math, re, sys
from collections import Counter, defaultdict
import numpy as np
rng = np.random.default_rng(20260912)
rows = list(csv.reader(open('V-08-uttrekk.tsv', encoding='utf-8'), delimiter='\t'))
cols = ['orgnr','opened','utfall','t_inn','t_avs','oppbud','tingrett','bransje','fy','total_assets','operating_revenue','amount_unit','currency','source_name','har_regnskap']
recs = [dict(zip(cols, r)) for r in rows]
assert len(recs) == 5165, len(recs)

def wilson(k, n, z=1.959964):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k/n; d = 1+z*z/n; c = (p + z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return (c-h, c+h)

def newcombe(k1, n1, k2, n2):
    l1, u1 = wilson(k1, n1); l2, u2 = wilson(k2, n2); p1 = k1/n1; p2 = k2/n2; d = p1-p2
    return (d - math.sqrt((p1-l1)**2 + (u2-p2)**2), d + math.sqrt((u1-p1)**2 + (p2-l2)**2))

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

km = {}
for r in csv.DictReader(open('B3-02-klassifisering.tsv', encoding='utf-8'), delimiter='\t'):
    km[norm(r['etikett'].replace('<NL>', ' '))] = int(r['bygg_F'])

n_bygg_mapped = 0
for x in recs:
    x['oppbud'] = int(x['oppbud'])
    x['inn'] = x['utfall'] == 'innstilt'
    x['t'] = int(x['t_inn']) if x['t_inn'] else None
    ta = float(x['total_assets']) if x['total_assets'] else None
    x['ta'] = ta
    x['bal'] = 'uten_regnskap' if ta is None else ('5M+' if ta >= 5e6 else ('1-5M' if ta >= 1e6 else 'under1M'))
    b = km.get(norm(x['bransje']))
    x['bygg'] = b
    if b is not None:
        n_bygg_mapped += 1
    x['w730'] = x['opened'] <= '2024-08-24'
    x['inn730'] = x['t'] is not None and x['t'] <= 730
    x['inn91'] = x['t'] is not None and x['t'] <= 91
    x['inn183'] = x['t'] is not None and x['t'] <= 183
    x['inn365'] = x['t'] is not None and x['t'] <= 365

print('sanity', len(recs), sum(x['inn'] for x in recs), sum(x['utfall'] == 'avsluttet' for x in recs), sum(x['utfall'] == 'aapen' for x in recs), 'oppbud', sum(x['oppbud'] for x in recs))
print('bygg mapped', n_bygg_mapped, 'of', len(recs), '; bygg=1:', sum(1 for x in recs if x['bygg'] == 1))
units = Counter((x['amount_unit'], x['currency'], x['source_name']) for x in recs if x['ta'] is not None)
print('amount_unit x currency x source (with total_assets):', dict(units))
for u in sorted(set(x['amount_unit'] for x in recs if x['ta'] is not None)):
    v = sorted(x['ta'] for x in recs if x['ta'] is not None and x['amount_unit'] == u)
    print('  unit', repr(u), 'n', len(v), 'median', v[len(v)//2])
print('balance coverage', sum(1 for x in recs if x['ta'] is not None), 'uten', sum(1 for x in recs if x['ta'] is None), '; har_regnskap (any year)', sum(int(x['har_regnskap']) for x in recs))
print('fy distribution', Counter(x['fy'] for x in recs if x['ta'] is not None))
bals = ['5M+', '1-5M', 'under1M', 'uten_regnskap']

def table(sub, ev, label):
    print('\n== ' + label + ' ==')
    for g in bals:
        s = [x for x in sub if x['bal'] == g]
        a = [x for x in s if x['oppbud'] == 1]; b = [x for x in s if x['oppbud'] == 0]
        ka = sum(x[ev] for x in a); kb = sum(x[ev] for x in b)
        print('  %-14s n=%5d oppbudsandel=%5.1f%%  oppbud %d/%d=%5.1f%%  ingen_felt %d/%d=%5.1f%%  diff=%+5.1f pp' % (g, len(s), len(a)/len(s)*100, ka, len(a), ka/len(a)*100, kb, len(b), kb/len(b)*100, (kb/len(b)-ka/len(a))*100))

def std_diff(sub, ev, strata_key):
    strata = defaultdict(list)
    for x in sub:
        strata[strata_key(x)].append(x)
    N = len(sub); d = 0.0; used = 0
    for k, s in strata.items():
        a = [x[ev] for x in s if x['oppbud'] == 1]; b = [x[ev] for x in s if x['oppbud'] == 0]
        if not a or not b:
            continue
        used += len(s)
        d += len(s)/N * (np.mean(b) - np.mean(a))
    return d*100, used

def boot(sub, ev, strata_key, B=2000):
    n = len(sub); out = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        out.append(std_diff([sub[i] for i in idx], ev, strata_key)[0])
    return np.percentile(out, [2.5, 97.5])

def contrast(sub, ev, label):
    a = [x for x in sub if x['oppbud'] == 1]; b = [x for x in sub if x['oppbud'] == 0]
    ka = sum(x[ev] for x in a); kb = sum(x[ev] for x in b)
    raw = (kb/len(b) - ka/len(a))*100
    lo, hi = newcombe(kb, len(b), ka, len(a))
    wa = wilson(ka, len(a)); wb = wilson(kb, len(b))
    print('\n### %s: oppbud %d/%d=%.1f%% [%.1f-%.1f]  ingen_felt %d/%d=%.1f%% [%.1f-%.1f]  raw diff %+.1f pp [%+.1f, %+.1f]' % (label, ka, len(a), ka/len(a)*100, wa[0]*100, wa[1]*100, kb, len(b), kb/len(b)*100, wb[0]*100, wb[1]*100, raw, lo*100, hi*100))
    d1, u1 = std_diff(sub, ev, lambda x: x['bal']); ci1 = boot(sub, ev, lambda x: x['bal'])
    print('   standardised for balance: %+.1f pp [%+.1f, %+.1f] (strata cover %d/%d)' % (d1, ci1[0], ci1[1], u1, len(sub)))
    sub2 = [x for x in sub if x['bygg'] is not None]
    d2, u2 = std_diff(sub2, ev, lambda x: (x['bal'], x['bygg'])); ci2 = boot(sub2, ev, lambda x: (x['bal'], x['bygg']))
    print('   standardised for balance x bygg: %+.1f pp [%+.1f, %+.1f] (n=%d, strata cover %d)' % (d2, ci2[0], ci2[1], len(sub2), u2))
    return raw, d1, ci1

w = [x for x in recs if x['w730']]
print('\n730-window n', len(w), 'innstilt<=730', sum(x['inn730'] for x in w), 'avsluttet<=730 (no innst)', sum(1 for x in w if not x['inn730'] and x['t_avs'] and int(x['t_avs']) <= 730))
table(recs, 'inn', 'AS-OF 24.08.2026: innstilt by balance x basis (all 5165)')
table(w, 'inn730', '730-DAY WINDOW: innstilt<=730 by balance x basis (n=3772)')
contrast(recs, 'inn', 'AS-OF innstilt (all 5165)')
contrast(w, 'inn730', '730-DAY WINDOW innstilt<=730 (n=3772)')
contrast(recs, 'inn91', 'innstilt within 91 d (all 5165)')
contrast(recs, 'inn183', 'innstilt within 183 d (all 5165)')
contrast(recs, 'inn365', 'innstilt within 365 d (all 5165)')

def bygg_contrast(sub, ev, label):
    s = [x for x in sub if x['bygg'] is not None]
    a = [x for x in s if x['bygg'] == 1]; b = [x for x in s if x['bygg'] == 0]
    ka = sum(x[ev] for x in a); kb = sum(x[ev] for x in b)
    raw = (ka/len(a) - kb/len(b))*100
    lo, hi = newcombe(ka, len(a), kb, len(b))
    def sd(sm):
        st = defaultdict(list)
        for x in sm:
            st[(x['bal'], x['oppbud'])].append(x)
        N = len(sm); d = 0
        for k, g in st.items():
            aa = [x[ev] for x in g if x['bygg'] == 1]; bb = [x[ev] for x in g if x['bygg'] == 0]
            if not aa or not bb:
                continue
            d += len(g)/N*(np.mean(aa)-np.mean(bb))
        return d*100
    out = []
    for _ in range(2000):
        idx = rng.integers(0, len(s), len(s)); out.append(sd([s[i] for i in idx]))
    ci = np.percentile(out, [2.5, 97.5])
    print('\n### BYGG %s: bygg %d/%d=%.1f%%  other %d/%d=%.1f%%  raw %+.1f pp [%+.1f,%+.1f]  standardised for balance x basis %+.1f pp [%+.1f, %+.1f]; bygg oppbudsandel %.1f%% vs %.1f%%' % (label, ka, len(a), ka/len(a)*100, kb, len(b), kb/len(b)*100, raw, lo*100, hi*100, sd(s), ci[0], ci[1], sum(x['oppbud'] for x in a)/len(a)*100, sum(x['oppbud'] for x in b)/len(b)*100))

bygg_contrast(recs, 'inn', 'as-of (all)')
bygg_contrast(w, 'inn730', '730-window')
print('\nopen as-of by basis:', {g: (sum(1 for x in recs if x['oppbud'] == g and x['utfall'] == 'aapen'), sum(1 for x in recs if x['oppbud'] == g)) for g in (1, 0)})
print('unresolved at 730 in window by basis:', {g: (sum(1 for x in w if x['oppbud'] == g and not x['inn730'] and not (x['t_avs'] and int(x['t_avs']) <= 730)), sum(1 for x in w if x['oppbud'] == g)) for g in (1, 0)})
