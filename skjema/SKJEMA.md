# Tabellkontrakten: hva skriptene leser, og hvordan du fyller det

Studiens skript er publisert slik de ble kjørt. De leser fra et lite sett tabeller i PostgreSQL. `skjema.sql` oppretter tabellene med de navnene skriptene bruker. Dette dokumentet sier hva en rad er, hvor verdiene kommer fra, og hvilke kolonner som faktisk brukes. Fyller du tabellene fra kildene under, kjører skriptene uendret.

*English summary at the end.*

## 1. Kildene

| Kilde | Hva du henter | Fyller |
|---|---|---|
| Brønnøysundregistrenes kunngjøringer, søk per organisasjonsnummer | Alle kunngjøringer for foretaket: dato, overskrift, hvilket register som kunngjorde, kunngjørings-id, og feltene på hver kunngjøringsside | `kunngjoring.kunngjoring`, `kunngjoring.insolvens`, `kunngjoring.felt`, `kunngjoring.selskap`, `kunngjoring.adresse`, `kunngjoring.kapital` |
| Enhetsregisteret, åpent API (`data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`) | Foretakets grunndata, også for slettede foretak | `company_intel.company`, `company_intel.brreg_ansatte` |
| Regnskapsregisteret, åpent API (`data.brreg.no/regnskapsregisteret/regnskap/{orgnr}`) | Siste innleverte årsregnskap i hele kroner | `company_intel.annual_account` |

Populasjonen er aksje- og allmennaksjeselskaper. For Del I trenger du kunngjøringene til hvert foretak med kunngjort konkursåpning i vinduet 1. september 2023 – 31. desember 2024, fulgt til 24. august 2026. For Del II trenger du i tillegg foretakene med «Tvangsoppløsning» eller «Tvangsavvikling» i samme vindu, og for kapittel 19 regnskap og grunndata.

## 2. `kunngjoring.kunngjoring`: alle kunngjøringer

Én rad per kunngjøring per foretak.

| Kolonne | Innhold |
|---|---|
| `orgnr` | Organisasjonsnummer, ni tegn |
| `kid` | Kunngjøringens id hos Brønnøysundregistrene (tallet i lenken til kunngjøringssiden) |
| `dato` | Kunngjøringsdato |
| `type` | Overskriften slik den står på kunngjøringssiden. På siden står overskrift og brødtekst i samme streng; lagre strengen som den er |
| `register` | Hvem som kunngjorde: `Foretaksregisteret`, `Regnskapsregisteret`, `Konkursregisteret`, eller tom |
| `type_kanon` | Beregnes automatisk av `kanoniser_type(type)`: den korte, stabile typen |

`kunngjoring.hendelsestype` fylles av innsettingen i `skjema.sql` etter at denne tabellen er lastet, og gir hver kanoniske type en kategori, om den avslutter foretakets liv, om den hører til insolvensløpet, og hvilket utfall den beviser. `v_hendelse` er tidslinjen skriptene leser: én rad per kunngjøring, ferdig merket.

## 3. `kunngjoring.insolvens`: insolvens- og avviklingskunngjøringene med feltene

Én rad per kunngjøring av disse typene, med feltene fra kunngjøringssiden:

`Konkurs - åpning`, `Konkurs - innstilling av bobehandlingen`, `Konkurs - avslutning av bobehandlingen`, `Fortsettelse av bobehandling`, `Tvangsoppløsning av aksjeselskap`, `Tvangsavvikling av aksjeselskap`, `Varsel om tvangsoppløsning`, `Sletting`, `Sletting etter fusjon`, `Sletting etter fisjon`.

| Kolonne | Innhold | Brukes i studien |
|---|---|---|
| `orgnr`, `dato`, `type` | Nøkkel; `type` er den kanoniske typen | Kohort og utfall (alle) |
| `tingrett` | Tingretten slik den er trykt | Rettskretsanalysen |
| `bostyrer` | Bostyrer slik det er trykt | Bare som «utfylt / ikke utfylt» |
| `saksnr` | Rettens saksnummer | Enhetskontroll |
| `fristdag` | Fristdagen etter dekningsloven | Tidsanalyse |
| `bransje` | Den trykte næringsangivelsen («Bransje/stilling») | Næringskartet |
| `kapital` | Kapitalangivelsen slik den er trykt | Del II |

## 4. `kunngjoring.felt`: alle navngitte felt

Kunngjøringssiden viser felt som etikett og verdi. Lagre hvert felt som én rad: `orgnr`, `dato` (kunngjøringsdato), `kunngj_type` (kanonisk type for kunngjøringen), `felt` (etiketten), `verdi` (teksten).

Feltene studien leser: `Åpnet etter` (verdien `Oppbud` der linjen finnes; linjen er ensidig, fravær betyr ikke «annen begjæring»), `Konkurs åpnet`, `Bransje/stilling`, `Revisor`, `Daglig leder`, `Organisasjonsform`.

## 5. `kunngjoring.selskap`, `adresse`, `kapital`: avledet av kunngjøringene

`selskap` har én rad per foretak: gjeldende navn, antall kunngjøringer, første og siste kunngjøringsdato, `stiftet` (datoen for «Nyregistrering»), `slettet` (første «Sletting …»), `konkurs_dato` (første «Konkurs - åpning»), `tvangs_dato` (første «Tvangsoppløsning …» eller «Tvangsavvikling …»), kapital ved registrering og siste kunngjorte kapital, organisasjonsform og siste formål. Alt kan regnes ut fra `kunngjoring.kunngjoring` og `kunngjoring.felt`.

`adresse` har adressefeltene fra «Nyregistrering» og «Endring av forretningsadresse»; `kapital` har beløpet fra feltet «Kapital» som tall, valuta og råtekst. Begge brukes bare i Del II.

## 6. `company_intel.company` og `brreg_ansatte`: Enhetsregisteret

Én rad per foretak fra det åpne API-et. Kolonnene som brukes: `orgnr`, `org_form_code` (organisasjonsform.kode), `industry_code_1` og `industry_text_1` (naeringskode1), `is_deleted` og `deleted_at` (slettedato), `last_submitted_accounts_year` (sisteInnsendteAarsregnskap). API-et svarer også for slettede foretak. `brreg_ansatte` er antallAnsatte og harRegistrertAntallAnsatte.

Merk at næringskoden ofte er tom for foretak som er slettet etter konkurs; studien bygger derfor næringskartet på den trykte næringsangivelsen i kunngjøringen, ikke på denne kolonnen.

## 7. `company_intel.annual_account`: Regnskapsregisteret

Én rad per foretak og regnskapsår, hele kroner. Feltnavnene i API-et står som kommentarer i `skjema.sql`. Sett `source_name` til `brreg_regnskapsregister`, `currency` og `amount_unit` til `NOK`. Studien bruker siste regnskapsår før åpningen (`total_assets`, `equity`, `liabilities`, `current_assets`, `operating_revenue`, `payroll_expenses`). Skriptene utelukker rader fra en tredjeparts regnskapskilde på `source_name`; med bare API-et lastet passerer alle rader.

Det åpne API-et gir siste innleverte årsregnskap. For foretak som gikk konkurs i vinduet er det normalt det samme regnskapet studien brukte.

## 8. Det som ikke kan hentes i dag

Rollene (registrert revisor ved åpningen, kapittel 19) leses fra Enhetsregisterets rolleoppslag, som ikke svarer for slettede foretak. Den variabelen kan derfor ikke bygges på nytt fra åpne kilder etter at foretaket er slettet.

## 9. Del II: uttrekksfiler

Del II-skriptene i Python leser flate filer under `del-2-tillegg/data/` som ble laget med SQL-filene i `del-2-tillegg/sporringer/` mot tabellene over. Hvert skript oppgir i toppen hvilken fil det leser, og SQL-filen med samme prefiks lager den. To formater er faste:

- `data/F-tvang-worklist.tsv`: tabulatorskilt uten overskrift, kolonnene `orgnr`, `tv_dato` (vedtaksdato), `inn` (dato for første innstilling), `avs` (dato for første avslutning), `avs_kid`, `konk_for`, `konk_etter` (konkursåpning før/etter vedtaket). Bygges fra `v_hendelse`.
- `data/H-avslutning-pages/<orgnr>-<kid>.html.gz`: avslutningskunngjøringenes sider, én fil per kunngjøring, som `workflow-final/D1-parse.py` leser dividendesetningen fra.

## 10. Kjøring

Del I: Node 20 eller nyere, `npm install pg`. Tilkoblingen leses av `del-1-hovedstudien/sporringer/db.mjs` fra miljøvariabelen `INTEL_DATABASE_URL`, eller fra `INTEL_PG_HOST`, `INTEL_PG_PORT`, `INTEL_PG_USER`, `INTEL_PG_PASSWORD`, `INTEL_PG_DB` (også fra en `.env`-fil i depotets rot). Kohortbyggingen er `kohort-10-frys.mjs`, hovedanalysen `kohort-20-analyse.mjs`, kumulativ insidens og de øvrige estimatorene fra revisjonen ligger i `rev2-*.mjs`, rettskretsene i `domstol-07-hovedanalyse.mjs` og `domstol-11-sluttabeller.mjs`, næringstabellene i `bransje-08-*` og `bransje-09-*`. Hvert skript sier i toppen hva det leser og skriver.

Del II: Python 3.11 eller nyere med `numpy`, `scipy`, `pandas`.

## 11. Kontrollpunkter etter lasting

- `kunngjoring.hendelsestype` skal ha én rad per kanonisk type; `Konkurs - åpning` skal ha `utfall = 'konkurs'` og `er_insolvensspor = true`.
- Foretak med første `Konkurs - åpning` i vinduet, organisasjonsform AS eller ASA, etter reglene i studiens kapittel 11: 5 165. Listen ligger i `kohort/konkurs-5165.txt`.
- Foretak med første «Tvangsoppløsning» eller «Tvangsavvikling» i vinduet: 2 571. Listen ligger i `kohort/tvangsavvikling-2571.txt`.
- Deretter: talljournalene, tall for tall.

---

## English summary

The scripts read a small set of PostgreSQL tables; `skjema.sql` creates them with the names the scripts use. Fill them from Brønnøysundregistrene's announcement pages (one row per announcement, plus the labelled fields on each page), from the open Enhetsregisteret API (company master data, also for deleted companies) and from the open Regnskapsregisteret API (last filed accounts, whole NOK), then run the scripts unchanged. Section 3 lists the announcement types and page fields the study uses; section 9 gives the two fixed file layouts for Del II; section 11 gives the checkpoints, starting with the two published cohort lists. One variable cannot be rebuilt from open sources today: auditor registered at opening, because the roles endpoint does not answer for deleted companies.
