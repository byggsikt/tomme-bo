# Kjøring: rekkefølge, arbeidsmapper og mellomfiler

Dette er kjørekartet for skriptene, slik de ble kjørt. Tabellkontrakten (`skjema/`) sier hva som må ligge i databasen; dette dokumentet sier hvilket skript som kjøres fra hvor, hva det leser, og hva det skriver. Kjørekartet er skrevet ut fra koden og kjøringene hos Byggsikt; det er ikke prøvd på en tom database utenfor Byggsikt.

*English summary at the end.*

## 0. Forutsetninger

- PostgreSQL 14 eller nyere med `skjema/skjema.sql` kjørt og tabellene fylt (se `skjema/SKJEMA.md`).
- Node 20 eller nyere og pakken `pg` (`npm install pg` i depotets rot). Tilkobling via miljøvariabler, se `del-1-hovedstudien/sporringer/db.mjs`.
- Python 3.11 eller nyere med `numpy`, `scipy`, `pandas`.
- **Arbeidsmappe for Del I:** depotets rot. Skriptene bruker `ROOT = "./del-1-hovedstudien"` og skriver under `del-1-hovedstudien/data/` og `del-1-hovedstudien/figurer/`.
- **Arbeidsmappe for Del II:** skriptets egen mappe (`del-2-tillegg/sporringer/`, `verifikasjon/` eller `workflow-final/`). Mellomfiler ligger i `del-2-tillegg/data/`, som må opprettes.
- Mellomfilene under `data/` er ikke publisert, bortsett fra kodelistene. Hver av dem lages av et skript eller en spørring som står i tabellene under.

## 1. Del I: kohort, hovedtall, næring, rettskrets

Kjør fra depotets rot: `node del-1-hovedstudien/sporringer/<skript>.mjs`.

| Trinn | Skript | Leser | Skriver | Merknad |
|---|---|---|---|---|
| 1 | `kohort-10-frys.mjs` | databasen; `data/bransjekart-v3_2026-08-30.json` | `data/_kohort-rader-arbeidskopi.json` (én rad per bo, uten organisasjonsnummer), `data/kohort-sammendrag-<dato>.json`, CSV-er med aggregater | **Frysen.** Alt i trinn 5 leser denne filen |
| 2 | `kohort-20-analyse.mjs` | databasen | hovedtabellene (utfall, næring, varighet) som CSV under `data/` | hovedtallene i kapittel 3–7 |
| 3 | `kohort-30-ssb-kalibrering.mjs`, `bransje-15-ssb-kalibrering.mjs` | databasen; SSB-tabellene 09122 og 07165 (hentes av deg) | kalibreringstabellen | kapittel 12 |
| 4 | `bransje-08-kohort-og-bransjetabell.mjs`, `bransje-09-bransjetabell.mjs` | databasen; `data/bransjekart-v3_2026-08-30.json` | næringstabellene | kapittel 6 |
| 5 | `rev2-01-validering.mjs` … `rev2-09-sammenstilling.mjs` | `data/_kohort-rader-arbeidskopi.json` (ingen databasetilgang) | `data/rev2-*` | kumulativ insidens, Grays test, presisjon, standardisering, permutasjon: kapittel 8 og 13 |
| 6 | `domstol-07-hovedanalyse.mjs`, `domstol-11-sluttabeller.mjs`, `domstol-12-homogenitet-og-ankere.mjs`, `domstol-14-stratifisert-lane2bygg.mjs` | databasen; `data/domstol-navnekart.tsv` (fra `domstol-10-navnekart.mjs`) | `data/domstol-*.tsv`, `figurer/domstol-*.tsv` | kapittel 9. `domstol-01` til `domstol-06` er inventar og diagnose av rettskretsnavnene og kjøres først |
| 7 | `rev3-01-fortsettelse-etter-endepunkt.mjs`, `sluttred-01-reassembler.mjs`, `sluttred-02-cif-kanonisk.mjs` | databasen og frysen | de endelige tabellene slik de ble publisert | sluttredaksjonen 30. august |
| 8 | `kontroll-01-kjerne.mjs` … `kontroll-05-kanonisk-stat.mjs`, `revisor-01-stikkprover.mjs` | databasen | kontrollutskrifter | uavhengige beregningsveier, kapittel 13.9 |
| 9 | `figurer/svg/gen/figur-*.py` | CSV/TSV under `data/` og `figurer/` | `figurer/svg/*.svg` | kjøres fra `figurer/svg/gen/` |

`kohort-00-rekon.mjs` til `kohort-06-rekon6.mjs` er rekonstruksjonsrundene fra august, før frysen. De trengs ikke for resultatene; de viser hvordan kohortdefinisjonen ble til. `bransje-00` til `bransje-07` og `kohort-03`/`kohort-07` bygde næringskartet, som ligger ferdig i `data/`. `_lib.mjs` og `kohort-bransjeklassifikator.mjs` er biblioteker.

## 2. Del II: dividende, tvangsavvikling, prediktorer

SQL-filene kjøres mot databasen og resultatet lagres som fil med samme navn under `del-2-tillegg/data/` (`psql --csv` for `.csv`, `psql -tA -F '\t'` for `.tsv`/`.txt`). Python-skriptene kjøres fra sin egen mappe og finner `data/` som `../data/`. Filene fra Del I (`_kohort-rader-arbeidskopi.json`, `bransjekart-v3_2026-08-30.json`) leses som `../../del-1-hovedstudien/data/…`.

| Kjede | Rekkefølge | Mellomfiler | Resultat |
|---|---|---|---|
| B1, åpningsgrunnlag | `B1-01-master.sql` → `B1-02-analysis.py` → `B1-03-supplement.py` | `B1-01-master.tsv`, `B1-cohort-tagged.tsv` | `B1-tables.md`, `B1-supplement-tables.md`, `B1-results.json` |
| B2, prediktorer | `B2-03-postnr.sql`; uttrekket `B2-01-extract.csv` lages av spørringen i `B2-analyse.py` → `B2-analyse.py` | `B2-01-extract.csv`, `B2-03-postnr.csv`, `B2-per-estate.csv` | `B2-tables.md`, `B2-model-*.json` |
| B3, byggmekanisme | `B3-01-kohort-pull.sql` → `B3-02-klassifiser.mjs` → `B3-05-analyse.py` → `B3-06-oppfolging.py`, `B3-07-omsetning.py` | `B3-01-kohort-pull.txt`, `B3-02-klassifisering.tsv`, `B3-03-kohort-klassifisert.tsv`, `B3-05-analysedata.tsv` | `B3-05-results.md`, `B3-06-oppfolging.md`, `B3-07-omsetning.md` |
| B5, plausibilitet og timing | `B5-01` … `B5-05`, `B5-07` (SQL) → `B5-06-analyse.py`, `B5-08-plausibilitet.py`, `B5-09-storrelse-og-standardisering.py`, `B5-12-bygg-standardisering.py`, `B5-13-felles-standardisering.py` | `B5-0N-*.txt`, `B5-05-kohortuttrekk.tsv` | `B5-*.txt` |
| F, tvangsavvikling | `F-tvang-worklist.tsv` og `F-tvang-profil.tsv` bygges fra `v_hendelse` og `annual_account` (kolonner i `skjema/SKJEMA.md` § 9 og i skriptenes topptekst) → `F-analyse-utfall.py` → `F-profil-analyse.py` | `F-tvang-worklist.tsv`, `F-tvang-profil.tsv`, `F-avslutning-dividende-parsed.jsonl` | kapittel 17 |
| D1, dividende | avslutningskunngjøringenes sider lagres som `data/H-avslutning-pages/<orgnr>-<kid>.html.gz` → `workflow-final/D1-parse.py` | `H-avslutning-worklist.tsv`, `B1-cohort-tagged.tsv` | `D1-parsed.tsv`, `D1-avvik.tsv`; talljournalens rad I1–I9 |
| D2, revisor ved åpning | `workflow-final/D2-01-revisor-ved-apning.sql` → `D2-sjekkliste.py`, `D2-02-avstemming-vb2.py`, `D2-03-modellA-alle-OR.py` | `D2-01-revisor-ved-apning.csv`, `B2-per-estate.csv`, `V-B2-03-extract.csv`, `V-B2-04-revisorfelt.csv` | `D2-resultater.md`, `D2-03-modellA-alle-OR.md` |
| V, gjenkjøringer | `verifikasjon/V-*.sql` → `V-*.py`/`.mjs` i nummerrekkefølge per gruppe (V-B1, V-B2, V-B3) | `V-B1-02-master.tsv`, `V-B1-04-tagged.tsv`, `V-B2-03-extract.csv`, `V-B2-core.pkl`, `V-B3-01-kohort.txt`, `V-B3-02-kohort-klassifisert.tsv`, `V-B3-02b-varsel.txt` | `V-*-results.json`, `V-B2-11-bands.md`, `V-B2-12-splits.md` |

Spørringene under `A2-sql-*` og `B4-*` er sonder og enkeltspørsmål (feltsemantikk, hva kunngjøringene bærer) som skriver én utskrift hver. `pivot.py` formaterer to av dem.

## 3. Kontrollpunkter

1. Etter trinn 1 i Del I: `kohort-sammendrag-<dato>.json` skal gi 5 165 bo; fingeravtrykket i `metodegrunnlag.json` og listen i `kohort/konkurs-5165.txt`.
2. Etter trinn 2 og 5: talljournalens rader (`del-1-hovedstudien/TALLJOURNAL.md`), tall for tall.
3. Etter Del II: `del-2-tillegg/TALLJOURNAL-TILLEGG.md`.

## 4. Kjent gap

Rekkefølgen og filene over er lest ut av koden og kjøringene hos Byggsikt. Ingen utenfor Byggsikt har kjørt kjeden på en tom database ennå. Den første som gjør det, vil sannsynligvis finne små ting: en kolonne kontrakten beskriver løst, en filsti som forutsetter en bestemt arbeidsmappe. Meld dem som issues; de rettes i depotet.

---

## English summary

Run Del I from the repository root with Node 20 and `pg`; the freeze script `kohort-10-frys.mjs` writes the frozen cohort file that the revision scripts (`rev2-*`) read without database access, and the main tables come from `kohort-20-analyse.mjs`, the industry tables from `bransje-08/09`, the courts from `domstol-07/11/12/14`. Run Del II from each script's own folder: every SQL file is saved as a file of the same name under `del-2-tillegg/data/`, and the Python chains B1, B2, B3, B5, F, D1, D2 and V read those files in the order given in section 2. Checkpoints: 5 165 estates after the freeze, then the two ledgers row by row. Nobody outside Byggsikt has run the chain on an empty database yet; the first run will find small packaging issues, and they are welcome as issues.
