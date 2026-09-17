#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D1-parse.py — uavhengig gjenparsing av de 923 lagrede avslutningskunngjøringene.

Skrevet fra bunnen av for verifikasjonslanen D1. Importerer ingenting fra
innsamlingskoden (ikke publisert); leser kun de gzippede råsidene i
data/H-avslutning-pages/<orgnr>-<kid>.html.gz.

Kjør:  python D1-parse.py   ->  skriver D1-parsed.tsv + D1-avvik.tsv og
                                printer alle tabeller til stdout.
"""
import collections
import csv
import glob
import gzip
import html
import json
import os
import re
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PAGES = os.path.join(ROOT, 'data', 'H-avslutning-pages')
WORKLIST = os.path.join(ROOT, 'data', 'H-avslutning-worklist.tsv')
COHORT = os.path.join(ROOT, 'data', 'B1-cohort-tagged.tsv')
ASSIST = os.path.join(ROOT, 'data', 'H-avslutning-dividende-parsed.jsonl')
OUT = os.path.dirname(os.path.abspath(__file__))

PRIO_SET = {'PRIO_I', 'PRIO_II', 'PRIO_III', 'PRIO_U'}

# ---------------------------------------------------------------------------
# 1. Råsiden -> ren tekst
# ---------------------------------------------------------------------------


def page_text(path):
    """Leser <orgnr>-<kid>.html.gz, dekoder latin-1 og klipper ut selve
    kunngjøringen (Altova-fragmentet) som ren tekst."""
    raw = gzip.open(path, 'rb').read()
    doc = raw.decode('latin-1')
    m = re.search(r'<h3><span>(.*?)</span></h3>', doc, re.S)
    if not m:
        return None, None, doc
    end = doc.find('</body></html>', m.start())
    if end < 0:
        end = len(doc)
    seg = doc[m.start():end]
    kind = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
    s = re.sub(r'<br\s*/?>', '\n', seg)
    s = re.sub(r'</tr>', '\n', s)
    s = re.sub(r'</td>', ' | ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n\s*\n+', '\n', s)
    return kind, s.strip(), doc


# ---------------------------------------------------------------------------
# 2. Normalisering av kravklasse (mine regler)
# ---------------------------------------------------------------------------
# Klassene i dekningsloven kap. 9:
#   PRIO_I   fortrinnsberettiget krav av første klasse (dl. § 9-3, lønn)
#   PRIO_II  fortrinnsberettiget krav av annen klasse  (dl. § 9-4, skatt/mva)
#   PRIO_U   «prioriterte krav» uten klassetall — prioritert, ikke plasserbar
#   UPRIO    alminnelig (uprioritert) krav             (dl. § 9-6)
#   ETTER    etterprioritert krav                      (dl. § 9-7)
#   ALLE     «alle krav» -> PRIO_I + PRIO_II + UPRIO + ETTER samtidig
#   MASSE    massekrav (kkl. § 138) — forekommer ikke i dette korpuset


def norm_class(raw):
    """raw = ordrett strengen mellom «dividende til» og «, jf. konkursloven».
    Returnerer (sett av klassekoder, normalisert etikett, flagg)."""
    s = raw.strip().lower().replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s).strip(' .,:;')

    # skrivefeil og synonymer i STAMMEN (aldri i klassetallet)
    stem = [
        (r'\bpriotiterte\b', 'prioriterte'),
        (r'\bprioriterete\b', 'prioriterte'),
        (r'\bpriorityerte\b', 'prioriterte'),
        (r'\bprioritert\b', 'prioriterte'),
        (r'\bprioritet\b', 'prioriterte'),
        (r'\buproriterte\b', 'uprioriterte'),
        (r'\bfordringer\b', 'krav'),
        (r'\bfordring\b', 'krav'),
    ]
    for pat, rep in stem:
        s = re.sub(pat, rep, s)
    s = re.sub(r'\bkrav av\b', 'krav', s)          # «krav av kl. I»
    # kl. / kl / kl: / kl, -> klasse  (lookahead: aldri inni ordet «klasse»)
    s = re.sub(r'\bkl(?!asse)[.:,]?\s*', 'klasse ', s)
    s = re.sub(r'\bklasse klasse\b', 'klasse', s)
    s = re.sub(r'\s+', ' ', s).strip()

    flags = []
    num = None
    m = re.search(r'\bklasse (i{1,3}|1|2|3)\b', s)
    if m:
        num = {'i': 1, 'ii': 2, 'iii': 3, '1': 1, '2': 2, '3': 3}[m.group(1)]
    elif re.fullmatch(r'i{1,3}', s):               # bare «I»
        num = {'i': 1, 'ii': 2, 'iii': 3}[s]
        flags.append('bare_romertall_klassenavn_mangler')
        s = 'prioriterte krav klasse ' + s

    has_u = bool(re.search(r'\buprioriterte\b', s))
    has_e = bool(re.search(r'\betterprioriterte\b', s))
    has_p = bool(re.search(r'\bprioriterte\b', s)) and not has_u and not has_e
    bare_krav = bool(re.fullmatch(r'krav klasse (i{1,3}|1|2|3)', s))
    rom = {1: 'I', 2: 'II', 3: 'III'}

    if s == 'alle krav':
        return ({'PRIO_I', 'PRIO_II', 'UPRIO', 'ETTER'}, 'alle krav',
                flags + ['alle_krav'])
    if 'massekrav' in s:
        return ({'MASSE'}, 'massekrav', flags)
    if has_e:
        return ({'ETTER'}, 'etterprioriterte krav', flags)
    if has_u and num is not None:
        # «uprioriterte krav kl. II» — selvmotsigende: uprioriterte krav har
        # ingen klasser, «kl. II» finnes bare blant de fortrinnsberettigede.
        return ({'UPRIO'}, 'uprioriterte krav (med klassetall %s)' % rom[num],
                flags + ['selvmotsigende_uprioritert_med_klassetall'])
    if has_u:
        return ({'UPRIO'}, 'uprioriterte krav', flags)
    if has_p and num is not None:
        return ({'PRIO_%s' % rom[num]}, 'prioriterte krav klasse %s' % rom[num], flags)
    if has_p:
        return ({'PRIO_U'}, 'prioriterte krav (klasse ikke oppgitt)',
                flags + ['prioritert_uten_klassetall'])
    if bare_krav and num is not None:
        # «krav kl. 1» — klassetall uten klassenavn; klasse 1/2 finnes bare
        # blant de fortrinnsberettigede kravene.
        return ({'PRIO_%s' % rom[num]}, 'prioriterte krav klasse %s' % rom[num],
                flags + ['klassetall_uten_klassenavn'])
    return (set(), raw.strip(), flags + ['UPARSET_KLASSE'])


# ---------------------------------------------------------------------------
# 3. Feltuttrekk
# ---------------------------------------------------------------------------
RE_DIV = re.compile(
    r'med\s+utbetaling\s+av\s*([0-9]+(?:[.,][0-9]+)?)\s*%\s*dividende\s*til\s*'
    r'(.*?)\s*,?\s*jf\.\s*konkursloven\s*§?\s*([0-9]+)', re.S | re.I)
RE_DIV_LOOSE = re.compile(r'([0-9]+(?:[.,][0-9]+)?)\s*%\s*dividende', re.I)
RE_UTEN = re.compile(r'uten\s+(utlodning|utbetaling|dividende)', re.I)
RE_UTLDAG = re.compile(r'Utlodningsdag\s*([0-3]?\d\.[01]?\d\.\d{4})')
RE_SAKSNR = re.compile(r'Saksnr:?\s*\|?\s*([^|\n]+)')
RE_BOSTYRER = re.compile(r'Hos bostyrer\s+(.*?)\s+er bobehandlingen', re.S)
RE_COURT = re.compile(r'utlodning kan påklages til\s+(.*?)\s*\.\s*Klagefristen', re.S)
RE_ORGNR = re.compile(r'Organisasjonsnummer:?\s*\|?\s*([0-9][0-9 ]{8,14})')
RE_KREG = re.compile(r'Konkursregisteret\s*([0-3]?\d\.[01]?\d\.\d{4})')
RE_NAVN = re.compile(r'Navn/foretaksnavn:?\s*\|?\s*([^|\n]+)')


def parse_page(path):
    fn = os.path.basename(path)
    m = re.match(r'(\d{9})-(\d+)\.html\.gz$', fn)
    file_orgnr, file_kid = (m.group(1), m.group(2)) if m else (None, None)
    kind, txt, doc = page_text(path)
    r = {'fil': fn, 'fil_orgnr': file_orgnr, 'fil_kid': file_kid,
         'kunngjoringstype': kind, 'problem': [], 'dividende': [],
         'n_dividendesetninger': 0, 'uten_utlodning_tekst': False}
    if txt is None:
        r['problem'].append('INGEN_KUNNGJORINGSBLOKK')
        return r, ''
    mo = RE_ORGNR.search(txt)
    r['side_orgnr'] = mo.group(1).replace(' ', '') if mo else None
    mn = RE_NAVN.search(txt)
    r['navn'] = mn.group(1).strip() if mn else None
    ms = RE_SAKSNR.search(txt)
    r['saksnr'] = ms.group(1).strip() if ms else None
    mb = RE_BOSTYRER.search(txt)
    r['bostyrer'] = re.sub(r'\s+', ' ', mb.group(1)).strip() if mb else None
    mc = RE_COURT.search(txt)
    r['tingrett'] = re.sub(r'\s+', ' ', mc.group(1)).strip() if mc else None
    mu = RE_UTLDAG.search(txt)
    r['utlodningsdag'] = mu.group(1) if mu else None
    mk = RE_KREG.search(txt)
    r['kunngjort'] = mk.group(1) if mk else None
    ml = re.search(r'hent_alle\.jsp\?kid=(\d+)&(?:amp;)?sokeverdi=(\d+)', doc)
    r['lenke_kid'] = ml.group(1) if ml else None
    r['lenke_orgnr'] = ml.group(2) if ml else None

    r['uten_utlodning_tekst'] = bool(RE_UTEN.search(txt))
    hits = list(RE_DIV.finditer(txt))
    r['n_dividendesetninger'] = len(hits)
    for h in hits:
        pct = float(h.group(1).replace(',', '.'))
        klasser, etikett, flags = norm_class(h.group(2))
        if not klasser:
            r['problem'].append('UPARSET_KLASSE:' + h.group(2))
        r['dividende'].append({'pct': pct, 'raa_klasse': h.group(2).strip(),
                               'klasser': sorted(klasser), 'etikett': etikett,
                               'flagg': flags, 'lovhjemmel': '§' + h.group(3)})
    # sikkerhetsnett: prosentsatser med ordet «dividende» som HOVEDregexen ikke tok
    if len(RE_DIV_LOOSE.findall(txt)) != len(hits):
        r['problem'].append('LOS_DIVIDENDETREFF_%d_MOT_%d'
                            % (len(RE_DIV_LOOSE.findall(txt)), len(hits)))
    if not hits and not r['uten_utlodning_tekst']:
        r['problem'].append('INGEN_DIVIDENDESETNING_OG_INGEN_UTEN')
    for fld in ('saksnr', 'bostyrer', 'tingrett', 'utlodningsdag', 'kunngjort',
                'side_orgnr'):
        if not r.get(fld):
            r['problem'].append('MANGLER_' + fld.upper())
    if r['side_orgnr'] and file_orgnr and r['side_orgnr'] != file_orgnr:
        r['problem'].append('ORGNR_FIL_VS_SIDE')
    if r['lenke_kid'] and file_kid and r['lenke_kid'] != file_kid:
        r['problem'].append('KID_FIL_VS_LENKE')
    return r, txt


# ---------------------------------------------------------------------------
# 4. Hjelpere
# ---------------------------------------------------------------------------


def iso(d):
    if not d:
        return None
    dd, mm, yy = d.split('.')
    return '%s-%02d-%02d' % (yy, int(mm), int(dd))


def pct_fmt(n, d):
    return '%.1f' % (100.0 * n / d) if d else 'n/a'


def quart(v):
    v = sorted(v)
    if not v:
        return (None, None, None)
    if len(v) == 1:
        return (v[0], v[0], v[0])
    q = statistics.quantiles(v, n=4, method='inclusive')
    return (statistics.median(v), q[0], q[2])


# ---------------------------------------------------------------------------
# 5. Hovedløp
# ---------------------------------------------------------------------------


def main():
    files = sorted(glob.glob(os.path.join(PAGES, '*.html.gz')))
    rows = [parse_page(f)[0] for f in files]

    wl = {}
    with open(WORKLIST, encoding='utf-8') as fh:
        for line in fh:
            p = line.rstrip('\n').split('\t')
            if len(p) < 5 or not re.fullmatch(r'\d{9}', p[0]):
                continue
            wl[p[0]] = {'opened': p[1], 'innstilt': p[2] or None,
                        'avsluttet': p[3] or None, 'kid_hint': p[4]}

    coh = {}
    with open(COHORT, encoding='utf-8') as fh:
        for d in csv.DictReader(fh, delimiter='\t'):
            coh[d['orgnr']] = d

    ass = {}
    if os.path.exists(ASSIST):
        for line in open(ASSIST, encoding='utf-8'):
            d = json.loads(line)
            ass[d['orgnr']] = d

    recs, avvik = [], []
    for r in rows:
        o = r['fil_orgnr']
        w = wl.get(o)
        if w is None:
            avvik.append((o, 'IKKE_I_ARBEIDSLISTE', r['fil']))
            continue
        if iso(r.get('kunngjort')) != w['avsluttet']:
            avvik.append((o, 'DATO_SIDE_VS_ARBEIDSLISTE',
                          '%s vs %s' % (r.get('kunngjort'), w['avsluttet'])))
        if r.get('side_orgnr') != o:
            avvik.append((o, 'ORGNR_SIDE_VS_FILNAVN', str(r.get('side_orgnr'))))
        if r['kunngjoringstype'] != 'Konkurs - avslutning av bobehandlingen':
            avvik.append((o, 'FEIL_KUNNGJORINGSTYPE', str(r['kunngjoringstype'])))
        for p in r['problem']:
            avvik.append((o, 'PARSEPROBLEM', p))
        c = coh.get(o, {})
        klasser = set()
        for d in r['dividende']:
            klasser |= set(d['klasser'])
        upr = [d['pct'] for d in r['dividende'] if 'UPRIO' in d['klasser']]
        pri = [d['pct'] for d in r['dividende'] if set(d['klasser']) & PRIO_SET]
        recs.append({
            'orgnr': o, 'kid': r['fil_kid'], 'navn': r.get('navn'),
            'opened': w['opened'], 'innstilt': w['innstilt'] or '',
            'avsluttet': w['avsluttet'], 'kunngjort_side': iso(r.get('kunngjort')),
            'kid_hint': w['kid_hint'], 'ordinaer': '1' if w['innstilt'] is None else '0',
            'saksnr': r.get('saksnr'), 'bostyrer': r.get('bostyrer'),
            'tingrett_side': r.get('tingrett'),
            'utlodningsdag': r.get('utlodningsdag'),
            'har_dividendesetning': '1' if r['dividende'] else '0',
            'uten_utlodning_tekst': '1' if r['uten_utlodning_tekst'] else '0',
            'raa_klasse': '; '.join(d['raa_klasse'] for d in r['dividende']),
            'klasser': '|'.join(sorted(klasser)),
            'etikett': '; '.join(d['etikett'] for d in r['dividende']),
            'flagg': '|'.join(sorted({f for d in r['dividende'] for f in d['flagg']})),
            'pct': ';'.join('%.6f' % d['pct'] for d in r['dividende']),
            'pct_uprio': ('%.6f' % max(upr)) if upr else '',
            'pct_prio': ('%.6f' % max(pri)) if pri else '',
            'bygg': c.get('bygg', ''), 'oppbud': c.get('oppbud', ''),
            'nace': c.get('nace', ''), 'tingrett_kohort': c.get('tingrett', ''),
            'utfall_kohort': c.get('utfall', ''), 'i_kohort': '1' if o in coh else '0',
        })

    with open(os.path.join(OUT, 'D1-parsed.tsv'), 'w', encoding='utf-8',
              newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(recs[0].keys()), delimiter='\t')
        w.writeheader()
        for x in recs:
            w.writerow(x)
    with open(os.path.join(OUT, 'D1-avvik.tsv'), 'w', encoding='utf-8',
              newline='') as fh:
        w = csv.writer(fh, delimiter='\t')
        w.writerow(['orgnr', 'type', 'detalj'])
        for a in avvik:
            w.writerow(a)

    P = print
    P('D1 - uavhengig gjenparsing av %d sider' % len(rows))
    P('  filer                      : %d' % len(files))
    P('  rader i arbeidslisten      : %d' % len(wl))
    P('  matchet arbeidslisten      : %d' % len(recs))
    P('  kunngjoringstyper          : %s'
      % dict(collections.Counter(r['kunngjoringstype'] for r in rows)))
    P('  avvik totalt               : %d' % len(avvik))
    for k, v in collections.Counter(a[1] for a in avvik).most_common():
        P('      %-34s %d' % (k, v))
    P('  uten dividendesetning      : %d'
      % sum(1 for r in recs if r['har_dividendesetning'] == '0'))
    P('  sier «uten utlodning»      : %d'
      % sum(1 for r in recs if r['uten_utlodning_tekst'] == '1'))
    P('  dividendesetninger per side: %s'
      % dict(collections.Counter(r['n_dividendesetninger'] for r in rows)))
    P('  i kohorten B1              : %d av %d'
      % (sum(1 for r in recs if r['i_kohort'] == '1'), len(recs)))
    P('  utfall i B1                : %s'
      % dict(collections.Counter(r['utfall_kohort'] for r in recs)))

    ORD = [r for r in recs if r['ordinaer'] == '1']
    INN = [r for r in recs if r['ordinaer'] == '0']
    P('\n  ordinaert avsluttet (ingen innstilling) : %d' % len(ORD))
    P('  avsluttet etter tidligere innstilling   : %d' % len(INN))

    for navn, grp in (('ORDINAERT AVSLUTTEDE', ORD), ('ETTER INNSTILLING', INN)):
        P('\n=== %s (n = %d) ===' % (navn, len(grp)))
        cc = collections.Counter()
        for r in grp:
            for k in (r['klasser'].split('|') if r['klasser'] else ['(ingen)']):
                cc[k] += 1
        for k, v in cc.most_common():
            vals = [float(r['pct'].split(';')[0]) for r in grp
                    if k in r['klasser'].split('|')]
            md, p25, p75 = quart(vals)
            P('  %-8s %4d  (%5s %%)  median %6.2f  P25 %6.2f  P75 %6.2f  '
              'min %.2f maks %.2f'
              % (k, v, pct_fmt(v, len(grp)), md, p25, p75, min(vals), max(vals)))
        nu = sum(1 for r in grp if 'UPRIO' in r['klasser'].split('|'))
        npz = sum(1 for r in grp if set(r['klasser'].split('|')) & PRIO_SET)
        only_p = sum(1 for r in grp if set(r['klasser'].split('|')) & PRIO_SET
                     and 'UPRIO' not in r['klasser'].split('|'))
        P('  -> med dividendesetning : %d/%d'
          % (sum(1 for r in grp if r['har_dividendesetning'] == '1'), len(grp)))
        P('  -> noe til uprioriterte : %d/%d = %s %%'
          % (nu, len(grp), pct_fmt(nu, len(grp))))
        P('  -> noe til prioriterte  : %d/%d = %s %%'
          % (npz, len(grp), pct_fmt(npz, len(grp))))
        P('  -> BARE til prioriterte : %d/%d = %s %%'
          % (only_p, len(grp), pct_fmt(only_p, len(grp))))
        u = [float(r['pct_uprio']) for r in grp if r['pct_uprio']]
        if u:
            md, p25, p75 = quart(u)
            P('  -> sats til uprioriterte: median %.1f  P25 %.1f  P75 %.1f  '
              'snitt %.1f  min %.2f maks %.2f'
              % (md, p25, p75, sum(u) / len(u), min(u), max(u)))
            P('     under 5 %%: %d   >= 25 %%: %d   = 100 %%: %d'
              % (sum(1 for x in u if x < 5), sum(1 for x in u if x >= 25),
                 sum(1 for x in u if x == 100)))
            for lab, lo, hi in (('0-1 %', 0, 1), ('1-5 %', 1, 5), ('5-10 %', 5, 10),
                                ('10-25 %', 10, 25), ('25-50 %', 25, 50),
                                ('50-100 %', 50, 100.0001)):
                P('     %-9s %d' % (lab, sum(1 for x in u if lo < x <= hi)))

    P('\n=== BYGG vs OVRIGE (ordinaert avsluttede) ===')
    for lab, sel in (('bygg', '1'), ('ovrige', '0')):
        g = [r for r in ORD if r['bygg'] == sel]
        nu = sum(1 for r in g if 'UPRIO' in r['klasser'].split('|'))
        u = [float(r['pct_uprio']) for r in g if r['pct_uprio']]
        P('  %-7s avsluttede %4d  uprioriterte fikk noe %3d = %5s %%  '
          'median sats %s'
          % (lab, len(g), nu, pct_fmt(nu, len(g)),
             ('%.1f' % statistics.median(u)) if u else 'n/a'))

    P('\n=== OPPBUD vs IKKE OPPBUD (ordinaert avsluttede) ===')
    for lab, sel in (('oppbud', '1'), ('ikke oppbud', '0')):
        g = [r for r in ORD if r['oppbud'] == sel]
        nu = sum(1 for r in g if 'UPRIO' in r['klasser'].split('|'))
        P('  %-12s avsluttede %4d  uprioriterte fikk noe %3d = %5s %%'
          % (lab, len(g), nu, pct_fmt(nu, len(g))))

    P('\n=== KOHORTNEVNERE (B1-cohort-tagged.tsv) ===')
    P('  kohort totalt   : %d' % len(coh))
    P('  bygg            : %d' % sum(1 for d in coh.values() if d['bygg'] == '1'))
    P('  ovrige          : %d' % sum(1 for d in coh.values() if d['bygg'] == '0'))
    P('  utfall          : %s'
      % dict(collections.Counter(d['utfall'] for d in coh.values())))
    P('  oppbud          : %s'
      % dict(collections.Counter(d['oppbud'] for d in coh.values())))

    P('\n=== DIFF mot data/H-avslutning-dividende-parsed.jsonl ===')
    dif = 0
    for r in recs:
        a = ass.get(r['orgnr'])
        if not a:
            P('  MANGLER i deres fil: %s' % r['orgnr'])
            continue
        ap = [round(d['pct'], 4) for d in a['dividende']]
        mp = [round(float(x), 4) for x in r['pct'].split(';') if x]
        if ap != mp:
            dif += 1
            P('  ULIK SATS %s  min %s  deres %s' % (r['orgnr'], mp, ap))
    P('  sider med ulik sats: %d av %d' % (dif, len(recs)))
    return recs, avvik


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
