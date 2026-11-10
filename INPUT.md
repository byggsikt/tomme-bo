# Inngangsdata: hva du må hente selv

Dette depotet inneholder metoden bak registerstudien «Tomme bo» (byggsikt.no/rad/tomme-bo/): kohortregler, estimatorer, klassifiseringsregler, kontrollspor og talljournal. Det inneholder **ikke** studiens egne datarader og **ikke** innsamlingskode. Alle inngangsdata er offentlige, og du henter dem selv fra kildene under. Den publiserte studien beskriver hver regel; koden her er koden som ble kjørt.

*English summary at the end.*

## 1. Kunngjøringer om konkursbehandling (Del I, kapittel 1–15)

**Kilde:** Brønnøysundregistrenes kunngjøringer (kunngjøringssøket på brreg.no og de tilhørende åpne tjenestene). Hver kunngjøring er offentlig og har en egen side med kunngjørings-id.

**Populasjon:** aksjeselskaper (AS) og allmennaksjeselskaper (ASA) med kunngjort konkursåpning i vinduet 1. september 2023 – 31. desember 2024, fulgt til observasjonsslutt (studien bruker 24. august 2026).

**Kunngjøringstyper du trenger, per foretak:**

| Hendelse | Hva den brukes til |
|---|---|
| Konkursåpning | Inngang i kohorten: *første observerte* åpning i vinduet |
| Innstilling av bobehandlingen (konkursloven § 135) | Utfall «innstilt» |
| Avslutning av bobehandlingen (utlodning, konkursloven § 128) | Utfall «ordinær avslutning»; teksten brukes i Del II |
| Fortsettelse av bobehandlingen (konkursloven § 139) | Gjenopptakelse etter innstilling (sju tilfeller i studien) |
| Sletting av foretaket | Slettingskonkordansen i kapittel 12 |

**Felter fra åpningskunngjøringen** (studien viser at alle fem er utfylt for hele kohorten): trykt næringsangivelse, tingrett, saksnummer, bostyrerangivelse (brukes bare som «utfylt / ikke utfylt») og fristdag. I tillegg kunngjøringsdato for hver hendelse og linjen «Åpnet etter: Oppbud» der den finnes (den er ensidig; fravær betyr ikke «annen begjæring»).

**Enheten er boet.** Første utfallskunngjøring på eller etter åpningen avgjør tilstanden: innstilt, ordinært avsluttet uten forutgående innstilling, eller uavgjort ved observasjonsslutt. Reglene for de seks boene med både innstilling og avslutning, for de tre foretakene med innstilling før åpning, og for ekstra kunngjøringer står i kapittel 11 i studien og i `del-1-hovedstudien/sporringer/kohort-*.mjs`.

**Kontroll:** organisasjonsnumrene i kohorten ligger i `kohort/konkurs-5165.txt`, og studien publiserer et fingeravtrykk, SHA-256 over de 5 165 numrene sortert stigende (`metodegrunnlag.json`). Bygg gjerne din egen kohort først og sammenlikn så listen eller fingeravtrykket; treff betyr at du har bygget nøyaktig samme kohort.

## 2. Næringskart (Del I, kapittel 6 og 11)

**Kilde:** Statistisk sentralbyrås Klass-API: SN2007 og SN2025 med korrespondansetabell 2919. Kopiene studien brukte, med hentedato, ligger i `del-1-hovedstudien/data/` sammen med kartet fra trykt næringsetikett til femsifret kode (`bransjekart-v3_2026-08-30.*`). Kartet er metode, ikke data om foretak.

## 3. Offisiell statistikk til kalibrering (Del I, kapittel 12)

**Kilde:** SSB statistikkbanktabell 09122 (foretakskonkurser etter næring) og 07165 (aksje- og allmennaksjeselskaper). Studien sammenlikner telleren mot disse; koden i `bransje-15-ssb-kalibrering.mjs`.

## 4. Avslutningskunngjøringenes fulltekst (Del II, kapittel 16)

**Kilde:** samme kunngjøringssider som i punkt 1. Dividendesetningen («… med utbetaling av X % dividende til …, jf. konkursloven § 128») leses fra teksten. Klassifiseringsregelen for kravklasse og de dokumenterte variantene av klassenavn ligger i `del-2-tillegg/workflow-final/D1-parse.py` og `del-2-tillegg/analyser/H-DIVIDENDE-*.md`.

## 5. Tvangsoppløsning og tvangsavvikling (Del II, kapittel 17)

**Kilde:** samme kunngjøringstjeneste; kunngjøringstypene «Tvangsoppløsning» og «Tvangsavvikling» i samme vindu, fulgt til utfall på samme måte. Brønnøysundregistrenes månedlige regneark over konkurser og tvangsavviklinger brukes til avstemming av antallet. Kohortlisten ligger i `kohort/tvangsavvikling-2571.txt`.

## 6. Årsregnskap og roller (Del II, kapittel 17 og 19)

**Kilde:** Regnskapsregisteret gjennom Brønnøysundregistrenes åpne API (`data.brreg.no/regnskapsregisteret`), som gir siste innleverte årsregnskap i hele kroner, og Enhetsregisteret for registrert revisor. Studien bruker siste balanse før åpningen (sum eiendeler) og om revisor var registrert ved åpningen.

## 7. Dokumentene i kapittel 18

Rapporten «Samfunnsøkonomisk analyse av permanente regler om rekonstruksjon» (2021), høringsnotatet av 13. januar 2023 og Prop. 56 L (2025–2026), alle på regjeringen.no. Referanselisten i studien gir sidetall og punkt.

## Hva du kan sammenlikne mot

`del-1-hovedstudien/metodegrunnlag.json` og talljournalene (`TALLJOURNAL.md`, `TALLJOURNAL-TILLEGG.md`) inneholder hvert publisert tall med teller, nevner og estimand. Kjernetallene: 5 165 bo; 3 897 innstilt (75,5 %); 917 ordinært avsluttet (17,8 %); 351 uavgjort (6,8 %); kumulativ insidens for innstilling ved 24 måneder 74,8 % [73,6–76,0] (Aalen–Johansen med ordinær avslutning som konkurrerende utfall).

## Hva som ikke er her, og hvorfor

- **Ingen regnskapsrader eller andre datarader om foretak.** Det eneste på foretaksnivå er de to kohortlistene i `kohort/`, organisasjonsnumre og ingenting annet.
- **Ingen innsamlingskode.** Hvordan du henter kunngjøringene, er ditt valg og ditt ansvar overfor kilden.
- **Skriptene leser fra tabellene i `skjema/skjema.sql`.** `skjema/SKJEMA.md` sier hva hver kolonne er og hvor verdien hentes, slik at du fyller tabellene fra kildene over og kjører skriptene uendret.

---

## English summary

This repository publishes the *method* behind the register study «Tomme bo» (Empty estates): cohort rules, estimators, classification rules, the audit trail and the number ledger. Apart from the two cohort identifier lists in `kohort/` (organisation numbers only), it does **not** publish the study's own data rows, and it contains no collection code. Every input is public: bankruptcy announcements from the Norwegian Register of Business Enterprises (Brønnøysundregistrene), SSB's industry code lists and statistics tables, the open annual-accounts API, and the cited government documents. Build your own event base from those sources following the published rules, then compare with the published cohort lists and fingerprints and with the published aggregates. The scripts read from the tables created by `skjema/skjema.sql`; `skjema/SKJEMA.md` says what each column is and where its value comes from, so you fill the tables from the sources above and run the scripts unchanged.
