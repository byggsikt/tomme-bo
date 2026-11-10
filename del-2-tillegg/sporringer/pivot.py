"""Pivot the A1-02 (announcement types) and A1-04 (felt keys) census files into markdown tables
with timing buckets (før / ved / etter åpning) as columns. Reads the psql -tA output; writes .md."""
import pathlib, collections
D = pathlib.Path(r"../data")
SEP = " | "
TID = {"1_for": "før", "2_ved": "ved", "3_etter": "etter"}

def rows(name):
    for line in (D / name).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("--STDERR--"):
            continue
        yield [c.strip() for c in line.split(SEP)]

# ---- A1-02: register | type_kanon | kategori | tid | rader | selskaper | unike_org_dato | forste | siste
piv = collections.OrderedDict()
for r in rows("A1-02-hendelsestyper-kohort.txt"):
    if len(r) < 9:
        continue
    reg, typ, kat, tid, rader, selsk, uod, forste, siste = r[:9]
    key = (typ, reg or "(blank)", kat or "(ikke i hendelsestype)")
    d = piv.setdefault(key, {"før": (0, 0), "ved": (0, 0), "etter": (0, 0), "forste": forste, "siste": siste})
    d[TID[tid]] = (int(rader), int(selsk))
    d["forste"] = min(d["forste"], forste); d["siste"] = max(d["siste"], siste)
out = ["| Kanonisk type | Register | Kategori | Før åpning (rader / selskaper) | Ved åpning | Etter åpning | Første dato | Siste dato |", "|---|---|---|---:|---:|---:|---|---|"]
for (typ, reg, kat), d in sorted(piv.items(), key=lambda kv: (-(kv[1]["før"][1] + kv[1]["ved"][1] + kv[1]["etter"][1]), kv[0])):
    f = lambda t: f"{d[t][0]:,} / {d[t][1]:,}".replace(",", " ") if d[t][0] else "–"
    out.append(f"| {typ} | {reg} | {kat} | {f('før')} | {f('ved')} | {f('etter')} | {d['forste']} | {d['siste']} |")
(D / "A1-02-pivot.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("A1-02 pivot:", len(piv), "type×register rows")

# ---- A1-04: type_kanon | felt | tid | rader | selskaper | n_verdier | n_raa_typer | snitt_lengde
piv2 = collections.OrderedDict()
for r in rows("A1-04-felt-nokler-kohort.txt"):
    if len(r) < 8:
        continue
    typ, felt, tid, rader, selsk, nv, nraa, avg = r[:8]
    key = (typ, felt)
    d = piv2.setdefault(key, {"før": (0, 0), "ved": (0, 0), "etter": (0, 0), "nv": 0, "avg": avg})
    d[TID[tid]] = (int(rader), int(selsk)); d["nv"] = max(d["nv"], int(nv))
# group by type: emit one table per type with felt rows; but for compactness, produce one long table
out = ["| Kunngjøringstype (kanonisk) | Felt (nøkkel) | Før åpning (rader / selskaper) | Ved åpning | Etter åpning | Distinkte verdier (maks per bucket) | Snitt lengde |", "|---|---|---:|---:|---:|---:|---:|"]
bytype = collections.defaultdict(list)
for (typ, felt), d in piv2.items():
    bytype[typ].append((felt, d))
def tot(d): return d["før"][1] + d["ved"][1] + d["etter"][1]
for typ in sorted(bytype, key=lambda t: -max(tot(d) for _, d in bytype[t])):
    for felt, d in sorted(bytype[typ], key=lambda x: -tot(x[1])):
        f = lambda t: f"{d[t][0]:,} / {d[t][1]:,}".replace(",", " ") if d[t][0] else "–"
        out.append(f"| {typ} | {felt} | {f('før')} | {f('ved')} | {f('etter')} | {d['nv']:,} | {d['avg']} |".replace(",", " "))
(D / "A1-04-pivot.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("A1-04 pivot:", len(piv2), "type×felt rows;", len(bytype), "types")
# felt keys that are person names (one-off keys) are noise: count how many felt keys appear for <=2 companies in total
noise = sum(1 for d in piv2.values() if tot(d) <= 2)
print("felt keys with <=2 companies total:", noise)
