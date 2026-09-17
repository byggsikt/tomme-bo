# Tomme bo — metode og kontrollspor

Dette er metodedepotet for registerstudien **«Tomme bo: tre av fire konkursbo etter norske aksjeselskaper lukkes uten midler»** (Byggsikt Data, publisert 30. august 2026, revidert september 2026): [byggsikt.no/rad/tomme-bo/](https://www.byggsikt.no/rad/tomme-bo/).

Studien følger 5 165 konkursbo etter aksje- og allmennaksjeselskaper, åpnet 1. september 2023 – 31. desember 2024, fra åpning til registrert utfall. Del II (kapittel 16–19) leser dividende fra avslutningskunngjøringene, måler tvangsavviklingsboene for samme vindu, leser regjeringens 90-prosenttall på nytt og undersøker hva som forutsier et tomt bo.

## Hva som ligger her

Alt som skal til for å gå fra offentlige kunngjøringer til studiens tall, slik det faktisk ble gjort:

| Mappe | Innhold |
|---|---|
| `INPUT.md` | Hvilke offentlige data du henter selv, og hvor |
| `kohort/` | Organisasjonsnumrene i de to kohortene (5 165 konkursbo, 2 571 tvangsavviklingsbo), sortert, med fingeravtrykk |
| `skjema/` | Tabellkontrakten: `skjema.sql` oppretter tabellene skriptene leser, `SKJEMA.md` sier hva hver kolonne er og hvor verdien hentes |
| `KJORING.md` | Kjørekartet: rekkefølge, arbeidsmapper, hvilket skript som lager hvilken mellomfil |
| `del-1-hovedstudien/sporringer/` | Kohortbygging, næringskart, rettskretser, kalibrering, figurgrunnlag (JavaScript) |
| `del-1-hovedstudien/data/` | Offentlige kodelister fra SSB Klass med hentedato, og kartet fra næringsetikett til kode |
| `del-1-hovedstudien/manus/` | Manuskriptet slik det er publisert, revidert 16. og 17. september 2026, med rettelseshistorikk (kapittel 13) |
| `del-1-hovedstudien/kilder/`, `del-2-tillegg/kilder/` | Litteraturgjennomgang, lovtekstuttrekk og kildeliste med fingeravtrykk over dokumentene studien brukte |
| `del-1-hovedstudien/TALLJOURNAL.md`, `metodegrunnlag.json` | Hvert publisert tall med teller, nevner og estimand; kohortfingeravtrykket |
| `del-2-tillegg/sporringer/`, `analyser/`, `verifikasjon/`, `workflow-final/` | Del II: dividendeparser, tvangsavvikling, prediktorer, gjenkjøringer |
| `del-2-tillegg/TALLJOURNAL-TILLEGG.md` | Talljournal for Del II: hvert tall med teller, nevner og kilde-skript |

## Hva som ikke ligger her

- **Ingen regnskapsrader eller andre datarader om foretak.** På foretaksnivå ligger de to kohortlistene i `kohort/` (organisasjonsnumre, ingenting annet) og de organisasjonsnumrene talljournalen bruker som eksempler når den forklarer en regel. Kunngjøringene bak dem er offentlige hos Brønnøysundregistrene.
- **Ingen innsamlingskode.** Hvordan du henter kunngjøringene, er ditt valg og ditt ansvar overfor kilden.
- **Ingen data fra tredjeparts regnskapsleverandører.** Studien bygger på kunngjøringer, SSB og Brønnøysundregistrenes åpne API.

## Slik etterprøver du

1. Hent inngangsdataene beskrevet i `INPUT.md`.
2. Opprett tabellene med `skjema/skjema.sql`, last inn dataene, og bygg kohorten med `del-1-hovedstudien/sporringer/kohort-*.mjs` etter reglene i studiens kapittel 11.
3. Sammenlikn din kohort med listene i `kohort/`, eller beregn SHA-256 etter oppskriften der og sammenlikn med fingeravtrykket. Treff betyr at du har nøyaktig samme kohort.
4. Kjør skriptene i rekkefølgen i `KJORING.md` og sammenlikn mot talljournalene.

Skriptene leser fra tabellene i `skjema/skjema.sql`. Opprett dem i din egen PostgreSQL, fyll dem fra kildene beskrevet i `skjema/SKJEMA.md` og `INPUT.md`, og kjør skriptene uendret.

## Status og forbehold

Studien er selvpublisert og ikke fagfellevurdert. Del I ble 30. august 2026 lest i sin helhet i en metodegjennomgang gjennomført med KI-verktøy, med tjue rettelsespunkter som alle er gjennomført; Del II er gjenberegnet i en separat kjøring, også med KI-verktøy. Ingen av gjennomgangene var en fagvurdering utført av insolvensjurister eller statistikere. Det er ikke dokumentert en ekstern rekonstruksjon fra selvstendig innhentede kildedata; det er dette depotet skal gjøre mulig.

Byggsikt arbeider i byggenæringen og har kommersiell interesse i risikoinformasjon om norske foretak. Ingen ekstern oppdragsgiver har påvirket studiens design eller rapportering.

## Om de publiserte kopiene

Én bevisst endring er gjort i kopiene her, og bare den: navn på KI-leverandører er erstattet med «KI-verktøy», i tråd med studiens egen omtale. Ingen tall, regler eller konklusjoner er endret. Interne arbeidsnotater, gjennomgangsrapporter, utkast og driftsrader om datainnsamling er ikke tatt med; kode, resultattabeller og talljournaler er komplette. Studiens metodegrunnlag fra 30. august 2026 sa at ingen foretaksliste skulle publiseres; den beslutningen ble omgjort 17. september 2026, og listene ligger i `kohort/`.

## Lisens

Kode: MIT. Tekst, dokumentasjon og figurgrunnlag: CC BY 4.0. Se `LICENSE` og `LICENSE-docs`.

## Sitering

Byggsikt Data (2026). *Tomme bo: tre av fire konkursbo etter norske aksjeselskaper lukkes uten midler.* Versjon 1.0, 30. august 2026, revidert september 2026. byggsikt.no/rad/tomme-bo/. Metode og kontrollspor: dette depotet.

---

*English:* This repository publishes the method behind the Norwegian register study «Tomme bo» (Empty estates): cohort rules, estimators, classification rules, number ledgers and review trail, as they were actually run. The only company-level content is the two cohort identifier lists in `kohort/` (organisation numbers only) and the organisation numbers the ledgers cite as examples when explaining a rule; there are no accounts rows and no collection code. All inputs are public; `INPUT.md` says what to fetch and where, and the lists and fingerprints let you verify that you rebuilt the same cohorts.
