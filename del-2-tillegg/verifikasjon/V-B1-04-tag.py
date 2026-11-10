# V-B1-04: independent construction tag + cohort sanity. Read-only inputs.
import json, collections, csv, sys, io
W = r"../data/"
S = r"./"
sys.stdout.reconfigure(encoding="utf-8")

frozen = json.load(open(S + "data/_kohort-rader-arbeidskopi.json", encoding="utf-8"))
# bransje label -> nace, must be a function
m = collections.defaultdict(set)
for r in frozen:
    m[r["bransje"].rstrip()].add(r["nace"])
amb = {k: v for k, v in m.items() if len(v) > 1}
print("frozen labels", len(m), "ambiguous label->nace", len(amb))
for k, v in list(amb.items())[:5]:
    print("  AMBIG", repr(k), v)
lab2nace = {k: list(v)[0] for k, v in m.items() if len(v) == 1}

rows = []
with open(W + "V-B1-02-master.tsv", encoding="utf-8", newline="") as fh:
    for line in fh:
        p = line.rstrip("\n").split("\t")
        rows.append(dict(orgnr=p[0], opened=p[1], innstilt=p[2] or None,
                         avsluttet=p[3] or None, basis=p[4], tingrett=p[5], bransje=p[6].replace(chr(60)*2+"NL"+chr(62)*2, chr(10))))
print("db rows", len(rows))

# label-set agreement between my DB extract and the frozen study extract
cdb = collections.Counter(r["bransje"].rstrip() for r in rows)
cfr = collections.Counter(r["bransje"].rstrip() for r in frozen)
print("labels db", len(cdb), "labels frozen", len(cfr))
print("labels only in db:", sorted(set(cdb) - set(cfr))[:10])
print("labels only in frozen:", sorted(set(cfr) - set(cdb))[:10])
diff = {k: (cdb.get(k, 0), cfr.get(k, 0)) for k in set(cdb) | set(cfr) if cdb.get(k, 0) != cfr.get(k, 0)}
print("labels with different counts:", len(diff))
for k, v in list(diff.items())[:10]:
    print("   ", repr(k), v)

def bygg(lab):
    n = lab2nace.get(lab.rstrip()) or ""
    return n.startswith("41.2") or n.startswith("42") or n.startswith("43")

for r in rows:
    r["bygg"] = bygg(r["bransje"])
    if r["innstilt"]:
        r["utfall"] = "innstilt"
    elif r["avsluttet"]:
        r["utfall"] = "avsluttet"
    else:
        r["utfall"] = "apen"

print()
print("SANITY utfall:", dict(collections.Counter(r["utfall"] for r in rows)))
print("SANITY basis :", dict(collections.Counter(r["basis"] for r in rows)))
print("SANITY bygg  :", dict(collections.Counter(r["bygg"] for r in rows)))
print("bygg x utfall:", dict(collections.Counter((r["bygg"], r["utfall"]) for r in rows)))
print("nace unknown label rows:", sum(1 for r in rows if r["bransje"].rstrip() not in lab2nace))

with open(W + "V-B1-04-tagged.tsv", "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t")
    w.writerow(["orgnr", "opened", "innstilt", "avsluttet", "basis", "tingrett", "bransje", "nace", "bygg", "utfall"])
    for r in rows:
        w.writerow([r["orgnr"], r["opened"], r["innstilt"] or "", r["avsluttet"] or "", r["basis"],
                    r["tingrett"], r["bransje"], lab2nace.get(r["bransje"].rstrip(), ""), int(r["bygg"]), r["utfall"]])
print("wrote V-B1-04-tagged.tsv")
