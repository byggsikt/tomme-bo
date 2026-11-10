# TALLJOURNAL — «Tomme bo: tre av fire konkursbo lukkes uten midler»

> **Presisering 17. september 2026.** Denne journalen er ført slik den ble skrevet i august og september 2026, og ordbruken er ikke endret i ettertid. To presiseringer gjelder ved lesing: (1) Gjennomgangene omtalt som «fagfellevurdering», «ekstern gjennomgang» og «uavhengig gjenkjøring» var metodegjennomganger gjennomført med KI-verktøy, ikke fagvurderinger av insolvensjurister eller statistikere, og studien er ikke fagfellevurdert. (2) Tallet 225 leses som 225 etter klassifiseringsregelen, 221 ved strengere lesning og 237 lest i dekningsrekkefølge; formuleringen «minst 225» brukes ikke lenger i studien. Studiens gjeldende tekst er byggsikt.no/rad/tomme-bo/ og manuskriptet i `manus/`.


**Autoritativ talljournal.** Forfatterne SKAL bruke tallene her, med forbeholdene her.
Satt av den uavhengige datakontrolløren 2026-08-30 etter adversariell revisjon av tre
researchlanes. Hvert tall er reprodusert i minst to uavhengige kjøringer med ulik
SQL-form der ikke annet er merket. Kontrollørens egne spørringer:
`sporringer/kontroll-01-kjerne.mjs` … `kontroll-05-kanonisk-stat.mjs`; frosset
kontrollresultat: `data/kontroll-kjerne-2026-08-30.json`.

**Verdikt: GO MED RETTELSER.** Kjernen holder. Briefens byggtall (1 142-familien) er
strøket og erstattet; en håndfull formuleringer og publiseringsfiler må rettes (se
MÅ-FIKSES nederst).

> **TILLEGG 2026-08-31 — FAGFELLEREVISJONEN.** En ekstern fagfellevurdering
> (rapporten er ikke tatt med i dette depotet) er gjennomført med
> tjue obligatoriske punkter. **Ingen av kjernetallene i A–G er endret** — en maskinell
> vakt asserterte de tolv låste tallene før revisjonen ble skrevet inn, 0 brudd. Det som
> er nytt, står i **seksjon I** nederst: fasthorisont-primærestimatet, Grays test,
> risikodifferansene, konfidensintervaller for varighet og hasardratio,
> proporsjonalitetsdiagnostikken, de differensielle sensitivitetsgrensene, de
> Holm-korrigerte domstolskontrastene, den utvidede standardiseringen og
> permutasjonstesten med 100 000 omstokkinger. Tre rader i D og E er merket
> [Revidert 2026-08-31]. Fem bindende bruksregler er lagt til (12–16).

---

## Bindende bruksregler

1. **Proveniens:** datagrunnlaget omtales i all publiseringsvendt tekst utelukkende som
   «offentlig tilgjengelige registerkunngjøringer» / «offentlige registre». Ingen
   interne tabellnavn, ingen omtale av datainnsamling, ingen «lane»-referanser i noe som
   skipper (to figurfilhoder må vaskes, se MÅ-FIKSES).
2. **Kohortdefinisjon (kanonisk):** distinkte foretak hvis **globalt første**
   kunngjorte «Konkurs - åpning» faller 2023-09-01..2024-12-31. (Vindu-første gir
   identisk mengde; differansen er målt til null. *Ordbruken «globalt første» er
   2026-08-31 presisert til «tidligste observerte» — se bruksregel 16; mengden er
   uendret.*) Kohortfingeravtrykk (sha256 over
   sortert orgnr-liste, beregnet i databasen, reprodusert av kontrolløren):
   `a5aea019c8157dca67e09580f154860f0b10419cff1ec79906a09f7edcc07452`.
3. **Utfallsregel (kanonisk):** utfall = første utfallskunngjøring **på/etter**
   åpningsdatoen. 3 foretak har i tillegg en eldre innstilling 111–177 dager FØR
   åpningen (tidligere konkursløp der åpningen er utgått hos kilden, L1); alle 3 har
   også innstilling etter åpningen og ER innstilt i dette løpet (kontroll-02).
4. **Tre-tilstandsfordelingen** er gjensidig utelukkende og summerer til kohorten:
   innstilt 3 897 / kun avsluttet 917 / fortsatt åpne 351 = 5 165. Tallet 923 er «har
   en avslutningskunngjøring uansett»; 6 bo har begge. **Aldri summer 3 897+923+351.**
5. **Bransje:** alltid fra åpningskunngjøringens trykte etikett (førstelinje ved
   flerlinjede etiketter), aldri fra næringskode på foretaket (død-NACE-fellen: bare
   7,6 % av kohorten har kode i registeret; 99,4 % av de slettede mangler den).
   Kart: `data/bransjekart-v3_2026-08-30.json` (SSB Klass v30 + v3218 +
   korrespondanse 2919). Kohortvinduet er vintage-rent (0 åpninger etter sømmen
   2025-09-01).
6. **Domstol:** fra åpningsradens tingrettsnavn. I kohortvinduet er navn ↔
   saksnummer-kode en perfekt 1:1-avbildning (23 navn, 23 koder, 0 uenige av 5 164
   parsebare; den ene resten er en kilde-typo som case-insensitiv parsing fanger).
7. **Avrunding:** andeler med én desimal (75,450 → **75,5**, aldri 75,4); antall som
   eksakte heltall; dager i hele dager (medianer av partall kan ende på ,5);
   konfidensintervaller er Clopper–Pearson 95 %, én desimal.
8. **Minstecelle:** hvert publisert antall ≥ 10. Gjelder også kolonnene
   avsluttet/åpne — dagens PUBLISERBAR-filer bryter dette og må reassembleres (se
   MÅ-FIKSES pkt. 2).
9. **Juridisk presisjon (skal stå i metodeboksen):** «innstilt» = bobehandlingen
   innstilt etter konkursloven § 135 fordi boets midler ikke dekker fortsatt
   bobehandling — uten utbetaling **fra boet** til kreditorene. Det betyr ikke at
   enhver kreditor fikk null: pantsikrede krav dekkes utenfor boet, og lønnskrav kan
   dekkes av lønnsgarantiordningen. (§ 135-innholdet er ankret i Ot.prp. nr. 26
   (1998-99), Del 4 punkt 1.1 — sitatet bærer både definisjonen og historikken.)
10. **Som-av-dato:** alle utfall er per korpusslutt **2026-08-24**; alle spørringer
    kjørt **2026-08-30**.
11. **Nyhetspåstand (korrigert 2026-08-30):** skriv **aldri** at tallet ikke er oppdatert
    offisielt siden 1996, at studien lukker et tretti år gammelt hull, eller at dette er
    «den første moderne oppdateringen». Det er uriktig — se H14–H18. Den forsvarlige
    påstanden er **nevneren**: studien er den første som måler utfallet for en avgrenset
    **åpningskohort**, fulgt til utfall med høyresensureringen målt, og den første som
    bryter tallet ned på byggfag og rettskrets. Litteraturtall fra proposisjonen (4 445,
    2 767, 3 005, 3 577, 2 652, 849, 1 691, 524, 4 375, 5 116) og de egne divisjonene av
    dem (62,2 / 68,7 / 69,9 / 63,8 / 63,3 %) er **kildens og våre avledninger, aldri
    studiens målinger** — de skal aldri stå i en tabell eller figur med studiens tall.
    *Skjerpet av verifikasjonen 2026-08-30:* skriv heller aldri at andelen «sist» ble
    tallfestet i 2023 — Prop. 56 L (2025–2026) gjentar 90-prosenttallet 27.03.2026 (H22).
    Nedbrytnings-førstheten formuleres alltid for **det kohortmålte tallet** og dagens
    offentlige publisering, aldri som at ingen noen gang har sammenliknet domstoler (H23).
12. **Estimandhierarki (nytt 2026-08-31):** primærresultatet er **24-måneders kumulativ
    insidens 74,8 %** [73,6–76,0] (Aalen–Johansen, ordinær avslutning som konkurrerende
    hendelse — I1). A2s **75,5 % er en OBSERVERT AS-OF-ANDEL** per 2026-08-24 med
    oppfølging 601–1 088 dager, og skal aldri omtales som en fasthorisont-sannsynlighet.
    Begge publiseres, alltid med etikett. Primær gruppekontrast er Grays test og
    risikodifferansen ved fast horisont (I2), ikke χ²-testen på as-of-andelene.
13. **Enheten er BOET (nytt 2026-08-31):** studien fastslår aldri en sannsynlighet eller
    dekningsgrad for en enkelt kreditor. Formuleringen «høyst om lag én av fire» er
    **STRØKET** og skal ikke gjeninnføres i noen form. Materialet inneholder verken antall
    kreditorer, kravstørrelser, prioritet, dividende eller dekning utenfor boet.
14. **Saksmiks-retningen (nytt 2026-08-31):** Ot.prp. nr. 23 (2003-2004) punkt 16.2 viser
    at **oppbud har den LAVESTE innstillingsandelen** (53 %) mot lønnstaker 80 %,
    skattefogd 77 % og skatteoppkrever 85 %. Skriv **aldri** at et oppbud typisk kommer fra
    et allerede tømt foretak. Kilden gir belegg for *at* rekvirenttypen skiller, ikke for
    retningen (H16, skjerpet).
15. **«Dekning» (nytt 2026-08-31):** G3/G4/G5 er **telleforhold**, ikke dekning. Et
    forholdstall over 100 kan aldri kalles dekning. Publiser alltid teller og nevner.
16. **Analyseenhet og «globalt første» (nytt 2026-08-31):** enheten er ett **bo-forløp**
    (orgnr + åpningsdato + saksnr). Kohortinngangen er foretakets **tidligste OBSERVERTE**
    åpning — ikke «globalt første», som kilden ikke kan bære på grunn av oppbevaringsgrensen.

---

## A — Kohort og hovedutfall

| # | Tall | Verdi | Kilde / kontroll | Forbehold |
|---|---|---|---|---|
| A1 | Kohort (foretak) | **5 165** | kohort-10/20, bransje-17, domstol-07 + kontroll-01 (×4, ulike SQL-former) | AS/ASA-forankret univers (se G3) |
| A2 | Innstilt (§ 135) | **3 897 = 75,5 %** [74,3–76,6] | kohort-20, bransje-17, domstol-07 + kontroll-01/02 | 75,450 % eksakt (75,45015); overskrift «tre av fire». Briefens 75,4 % var avkorting — strøket. [Rettet 2026-08-30: 75,451 var feilavrundet i siste siffer] |
| A3 | Kun avsluttet | **917 = 17,8 %** | bransje-17 + kontroll-01 | 923 bo har avslutningskunngjøring; 6 har begge → i tre-tilstandsform 917 |
| A4 | Fortsatt åpne per 2026-08-24 | **351 = 6,8 %** | alle laner + kontroll-01 | Løser seg over tid; oppgi alltid som-av-dato |
| A5 | Bo med begge kunngjøringer | **6** | alle laner + kontroll-01 | 1 av de 6 har også «Fortsettelse av bobehandling» (7 i hele kohorten) |
| A6 | Oppfølgingstid | **minst 601 dager (19,7 mnd), median 852, maks 1 088** | kohort-20 + kontroll-01 | ERSTATTER briefens «≥ 20 måneder» |
| A7 | Sum-kontroll | 3 897 + 917 + 351 = 5 165 | kontroll-01/05 | Binder A1–A4 |

## B — Bygg og næringsgrupper (kohortvinduet)

Primærdefinisjon i artikkelen: **utførende bygg og anlegg** (SN2007 41.2 + 42 + 43,
uten 41.1 eiendomsutvikling). Sekundær (metodeboks): hele næringsområde F (41–43).
Briefens byggtall **1 142 / 813 / 229 / 100 er STRØKET** — en SN2025-feid
oppslagstabell mistet 269 foretak (ni navngitte etiketter); den gamle mengden er en
ekte delmengde av den nye, mekanismen er reprodusert av to laner.

| # | Tall | Verdi | Kilde / kontroll | Forbehold |
|---|---|---|---|---|
| B1 | Bygg utførende: åpninger | **1 280** | kohort-20 + bransje-08 + kontroll-01 (to uavhengige klassifikatorer, 0 uenige foretak) | |
| B2 | Bygg utførende: innstilt | **911 = 71,2 %** [68,6–73,6] | samme | |
| B3 | Bygg utførende: avsluttet / åpne | **258 = 20,2 % / 111 = 8,7 %** | samme | |
| B4 | Bygg område F: åpninger, innstilt | **1 411 / 1 016 = 72,0 %** [69,6–74,3] | samme | Ikke stabil over sømmen 2025-09-01 (41.1 → 68.12 i SN2025) |
| B5 | Eiendomsutvikling (41.1): | **131 / 105 = 80,2 %** | samme | Verre enn byggfagene — del av historien |
| B6 | Øvrige næringer (komplement til utførende) | **3 885 / 2 986 = 76,9 %; åpne 6,2 %** | kohort-20 + kontroll-01 | ERSTATTER briefens 4 023 / 76,7 %. Komplement-par til B1–B3 (summerer til kohorten) |
| B7 | Bygg mot øvrige, utførende vs komplement | **−5,7 pp; χ²(Yates) 16,5; p = 4,8×10⁻⁵** | kontroll-05 | Overskriftsparet 71,2 mot 76,9 |
| B8 | Bygg mot øvrige, F vs øvrige ekskl. ren uoppgitt (120 bo) | **−4,1 pp; χ² 9,05; p = 0,0026; Newcombe-KI [−6,9, −1,5] pp** (to desimaler [−6,89, −1,45]) | bransje-18 + kontroll-05 + tallrevisjonen | [Rettet 2026-08-30: øvre grense −1,45 avrundes til −1,5, ikke −1,4.] Ekskluderes hele 155-bøtta: −4,1 pp; χ² 8,73; p = 0,0031 (tallrevisjonen) |
| B9 | Flere uavgjorte bo i bygg | **8,7 mot 6,2 %** (χ² 9,07, p = 0,0026); områdedef. 8,9 mot 6,2 % (χ² 11,05, p = 0,0009) | bransje-18 + kontroll-01 + tallrevisjonen | [Presisert 2026-08-30: 11,05 tilhører OMRÅDEdefinisjonen.] Rekkefølgen kan ikke snu: kryssingspunkt primærdef. x = 2,28, områdedef. x = 1,53 (frossen fil 1,5348) — begge > 1 |
| B10 | Uoppgitt/uklassifiserbar etikett | **155 / 143 = 92,3 %** | kohort-20 + kontroll-01 | PUBLISERBAR form (alle celler ≥ 10). Ren «Uoppgitt»-delmengde: 120/114 = 95,0 % — kun i metodenotat (ikke-innstilt-cellen er 6 < 10). Aldri omfordel bøtta. SSB har samme restkategori («Ikkje opplyst»): 110 mot våre 109 i kohortkvartalene |

## C — Byggfag (trykt etikett, førstelinje)

**Moden kohort 2023-08-24..2024-12-31** (briefens tabellvindu — beholdes fordi det er
identisk reprodusert av tre kjøringer og gir størst n):

| Fag | Verdi | KI95 |
|---|---|---|
| Snekkerarbeid | **138/178 = 77,5 %** | [70,7–83,4] |
| Grunnarbeid | **81/107 = 75,7 %** | [66,5–83,5] |
| Malerarbeid | **47/63 = 74,6 %** | [62,1–84,7] |
| Elektrisk installasjonsarbeid | **43/60 = 71,7 %** | [58,6–82,5] |
| Oppføring av bygninger | **415/600 = 69,2 %** | [65,3–72,8] |
| Rørleggerarbeid | **55/83 = 66,3 %** | [55,1–76,3] |

Kilder: bransje-13 + kontroll-01 (×3). Oppføring er 415/600 med
førstelinje-reparasjonen (ett foretak har flerlinjet etikett); briefens 414/599 var
eksaktmatch — bruk 415/600. Kanonisk vindu-variant (2023-09-01..) ligger i
`data/kohort-per-bransje-2026-08-30.csv` (Snekker 135/175 = 77,1 % osv.) — velg ETT
vindu i artikkelen og merk det.
**Bindende presentasjonsregel:** fagene presenteres som spenn med intervaller, ikke
rangering — ytterpunktene snekker mot rørlegger gir Fisher eksakt p = 0,069
(kontroll-01: 0,0688; ikke signifikant). Malerarbeid finnes ikke som eget fag etter
sømmen (SN2025 slår sammen maler- og glassarbeid).

## D — Varighet åpning → innstilling (kanonisk kohort, utførende-definisjonen)

| # | Tall | Verdi | Kilde / kontroll | Forbehold |
|---|---|---|---|---|
| D1 | Rå median, fullførte saker | **alle 152; bygg 179; øvrige 144,5 dager** (kvartiler bygg 101/312, øvrige 84/265,8) | kohort-20 + kontroll-03 | «Fullførte saker» MÅ stå — rå median er sensureringsbiasert og underdriver gapet. Briefens 174/140 (annet vindu) erstattes |
| D2 | Kaplan–Meier-median | **bygg 257; øvrige 203 dager** | kontroll-03 (v3-def); domstol-08 fikk 257/204 med eldre def | Sensureringsriktig hovedtall. Formuler «rundt to måneder lenger» |
| D3 | Kumulativ insidens (Aalen–Johansen), tid til 50 % innstilt | **bygg 267; øvrige 205 dager** (til 60 %: 389 mot 292) | kontroll-03; domstol-08 (eldre def: 273/207, 392/293) | Avslutning som konkurrerende hendelse |
| D4 | Innstilt-andel ved ett år | **bygg 57,2 %; øvrige 65,2 %** | kontroll-03 (domstol-08: 56,7/65,1) | **[Revidert 2026-08-31, verifikasjonen]** Manus siterer nå I1b (rev2-02, frosset uttrekk, kanonisk utfallsregel): **57,1 mot 65,2 %** — samme verdier som fasthorisont-tabellen i kap. 4, slik at manus ikke bærer to tall for samme estimand. kontroll-03s 57,2 er den databaserte veien der de 3 randtilfellene bærer en annen dato (metodegrunnlagets avvik nr. 2); differansen er ETT byggbo ved dag-365-grensen. Figurfila `domstol-modningskurve-cif.tsv` bærer fortsatt 57,2 (dag 364 = 732/1280) — se MÅ-FIKSES 11(d) |
| D5 | Tingrett-stratifisert mediandifferanse | **+38,4 dager** (19 strata, 3 749 saker) | kohort-20 + kontroll-05 (eksakt match) | Blokkerende krav innfridd: forskjellen blant FULLFØRTE saker blir større ved stratifisering (rå +34,5) — ikke en domstolseffekt. **[Revidert 2026-08-31]** Bootstrap-KI (klynget på rettskrets) **[24,0; 52,7] dager**; rå [21,0; 46,0]. Tellingen «bygg tregest i 18 av 19» er **STRØKET fra publisering** — det frosne uttrekket gir 17 av 19 og 3 747 saker, og tellingen vipper på ett bo i Vestre Innlandet (3 randtilfeller + én dublett i kontroll-05s ikke-dedupliserte join). Skriv «det store flertallet av kretsene». **D5 skal ALDRI sammenliknes med I3s +62 dager** — ulike estimander på ulike delmengder (bruksregel 12) |
| D6 | Stratifisert hasardratio (logrank/M-H), bygg mot øvrige | **HR 0,80**, KI95 **[0,745; 0,859]** (0,79–0,81 over fire definisjons-/sensureringsvarianter) | rev2-04 (to uavhengige implementasjoner, differanse 0) + domstol-08/14 | **[Revidert 2026-08-31]** z og p ERSTATTET: **z = −6,128, p = 8,90×10⁻¹⁰** (O−E = −168,52, V = 756,25, 23 strata). Briefens «z = −5,8; p ≈ 7×10⁻⁹» stammer fra domstol-08s eldre byggdefinisjon (1 142 bo) og reproduseres IKKE under noen av de fire kanoniske variantene (alle gir z mellom −6,10 og −6,44). HR-punktestimatet reproduseres eksakt. Cox (Breslow) gir 0,792 [0,734; 0,853]; klynge-robust (23 kretser) [0,724; 0,866]. **PH-ANTAKELSEN ER FORKASTET (I5)** — HR 0,80 er et VEKTET GJENNOMSNITT, aldri «vedvarende». Cox med flere kovariater er fortsatt IKKE kjørt |

## E — Domstoler (kanonisk kohort, navn fra åpningsraden)

| # | Tall | Verdi | Kilde / kontroll | Forbehold |
|---|---|---|---|---|
| E1 | Rettskretser i vinduet | **23** (perfekt 1:1 navn ↔ saksnr-kode; 0 uenige) | domstol-02 + kontroll-01 | Navnenormalisering unødvendig i vinduet; UTFALLSrader etter 2025-06-10 bærer etterfølgernavn (146 av 3 897 = 3,75 %, 0 kodebytter) — grupper ALLTID på åpningsraden |
| E2 | Publiserbare kretser (n ≥ 100) | **16 kretser, 4 698 saker (91,0 % av kohorten)** | domstol-11 + kontroll-01 | Lane 1s «15» i narrativet var feiltelling — datafilene sier 16 |
| E3 | Spenn innstillingsandel (n ≥ 100) | **66,8 %** (Hordaland [62,0–71,4]) **til 82,0 %** (Møre og Romsdal [76,7–86,6]) | ×3 | ERSTATTER briefens 67,6–81,6 (umodent vindu). Deskriptiv variasjon, IKKE rangering. Tellingen «5 av 120 par med ikke-overlappende KI» er reprodusert eksakt (6 med Wilson), men er **DESKRIPSJON, ikke test**. **[Revidert 2026-08-31]** Signifikanspåstander skal bæres av I6: Holm-korrigert overlever **3 av 120 par**, alle med Hordaland i den lave enden. Møre og Romsdal i den HØYE enden overlever IKKE (p_Holm = 0,178) — ingen krets i den høye enden kan omtales som avvikende |
| E4 | Spenn median dager (n ≥ 100) | **fullførte saker: 97 (Søndre Østfold) til 213 (Østre Innlandet)**; **sensureringsbevisst (CIF-median): 133 (Nord-Troms og Senja) til 322 (Agder)** | ×3 + rev2-06 | ERSTATTER briefens 96–204. **[Revidert 2026-08-31]** Domstolssammenlikninger skal bruke CIF-raden — fullførte-saker-medianen UNDERVURDERER spredningen mellom kretsene kraftig fordi kretsene har ulik andel uavgjorte bo. 24-mnd CIF per krets spenner 66,2–80,6 %. Den gamle enkeltkjørte KM-medianen 127–309 (eldre def) er strøket til fordel for CIF |
| E5 | Homogenitetstest | χ² 39,8, df 15, **p = 0,0005** | domstol-12 (én lane) | Variasjonen er reell, men saksmiks (oppbud vs begjæring) er uobserverbar — forbeholdet SKAL stå |
| E6 | Næringsmiks demper ikke domstolsvariasjonen | standardisert O/E-spenn **0,889–1,089** ≈ ustandardisert ratio-spenn 0,888–1,090 | domstol-11 + rev2-07 (tre stratifiseringer) | **[Revidert 2026-08-31]** Skriv **aldri** «næringsmiksen forklarer ingenting» — den forsvarlige setningen er «næringssammensetning dempet ikke variasjonen vesentlig under denne standardiseringen». Tallfesting: overskuddsheterogenitet 24,83 → 26,17 (ØKER 5,4 %); τ̂² 0,0269 → 0,0284 (+5,7 %). Robust over 74 tosifrede koder, 19 hovedområder og 46 sammenslåtte bøtter. Lane 3s spenn 0,888–1,085 skyldes en annen etikett→NACE-kilde; oppgi bøttekilden sammen med spennet |
| E9 | Hierarkisk domstolsmodell (ny 2026-08-31) | μ̂ = 1,1133 (75,28 %), **τ̂ = 0,164**; LRT 10,97, p = 4,6×10⁻⁴; krympet spenn **69,5–78,9 %** mot rå 66,8–82,0 % | rev2-06 | Random-effects-logit, ML via Gauss–Hermite; grensefordeling 0,5·χ²(0)+0,5·χ²(1). Kretsvise tall for de sju små kretsene publiseres IKKE (minstecelle) |
| E7 | Byggandel av porteføljen (n ≥ 100) | **15,7 % (Sør-Rogaland) til 34,8 % (Romerike og Glåmdal)** | kohort-20 + kontroll-01 (utførende-def) | Lane 3s 13,9–31,0 % var eldre def — bruk 15,7–34,8 |
| E8 | Samisk parallellnavn | Sis- ja Nuorta-Finnmárkku diggegoddi / **Indre og Østre Finnmark tingrett** | domstol.no (verifisert) | n = 26 → under n≥100-porten, men navnet må inn i enhver fulltabell |

## F — Modning, sensurering, vindusfølsomhet

| # | Tall | Verdi | Kilde / kontroll |
|---|---|---|---|
| F1 | Modningskurve (risikomengde): andel innstilt ved 3/6/12/18/24/30 mnd | **23,0 / 44,9 / 63,1 / 71,9 / 74,5 / 74,7 %** | kohort-20 + kontroll-01 (eksakt) |
| F2 | Bygg under øvrige på hver horisont | 24 mnd: **70,0 mot 76,0 %** | kohort-20 (én lane; kurveform bekreftet av D2–D4). **[Presisert 2026-08-31]** I1c (rev2-02) gir 69,9 mot 76,0 på de samme 934/2 838 boene — tellerne avviker med ett bo per gruppe (654/2 158 mot 653/2 157) mellom beregningsveiene; manus siterer begge med brobygging (kap. 4 og 10, § 13.9) |
| F3 | Naiv andel per åpningskvartal (ærlighetsfiguren) | platå **74,0–76,4 %** (2023K3–2024K4), deretter mekanisk fall 71,8/71,9 → 67,5/67,6 → 64,1/64,2 → 56,6/56,7 → 46,6 → **19,0 %** (2026K2) | kohort-20/domstol-09 + kontroll-01 (±0,1 pp mellom kjøringene — skyldes 3-foretaks-randen; uvesentlig) |
| F4 | Vindusfølsomhet | modne vinduer 75,1–75,6 %; ..2025-06: **73,9 %**; ..2025-12: **71,2 %**; ..korpusslutt: **62,4 %** | kohort-20 + kontroll-01 (eksakt) |
| F5 | Kohortkuttets begrunnelse | innstillingsserien starter **2023-08-25**, avslutningsserien **2023-06-02** (målt som tekst i basen) | kontroll-01 | ERSTATTER briefens 2023-08-24 / 2023-06-01 (tidssoneforskyvning i driveren) |

## G — Dekning og kalibrering (metodeboksen)

| # | Tall | Verdi | Kilde / kontroll | Forbehold |
|---|---|---|---|---|
| G1 | Innstillingsserien er sammenhengende | hver måned 2023-09..2026-07: **18–23 kunngjøringsdager, 135–349 foretak** | kohort-20 + kontroll-01 | Lavpunktene aug-24/aug-25 er rettsferien |
| G2 | Innstillingsserien er ett-registers | 9 978 av 9 979 kun fra Konkursregisteret | kohort-20 (én lane) | L8-dublettfellen gjelder åpningene, ikke utfallene |
| G3 | SSB-kalibrering, AS+ASA (tab. 07165), 2023K3–2026K2 | **11 174 mot 11 132 = 100,4 %** (kvartalsvis 99,2–102,9 %) | kohort-30 + kontroll-04 (eksakt) | Mot ALLE orgformer 87,4 % — differansen er enkeltpersonforetak; materialet er AS/ASA-forankret. Aldri formuler som «dekning over 100 %» — revisjonsetterslep + avgrensning |
| G4 | SSB-kalibrering, foretakskonkurser ekskl. ENK (tab. 09122, 2023K4–2024K4) | dekning **98,7 %** totalt, **98,9 %** bygg; byggandel **27,33 mot SSBs 27,27 %** | bransje-15 + kontroll-04 (eksakt) | Byggandelen er kalibrert; nivået er dekningsavhengig |
| G5 | Bygg-dekning over HELE perioden | med kanonisk SN2007-tilbakeføring **2 917 mot 2 910 = 100,2 %**; uten tilbakeføring av SN2025-etiketten faller serien kunstig ~10 % etter 2025K3 (lane 1 målte 2 827 = 97,1 %) | kontroll-04 + kohort-30 | L17-sømmen; kohortvinduet er upåvirket (0 åpninger etter sømmen) |
| G6 | Dekningsprøve på utfallsserien (innenfra) | av 4 814 bo med utfall er **4 799 (99,7 %) slettet i registeret**; av 351 åpne har **0** slettingskunngjøring og **2** er slettet → øvre grense for tapte utfall ≈ **2/5 165 = 0,04 %** | kohort-20 + kontroll-01 | Testen hviler på registerstatus (fullt sveip), ikke på en kunngjøringsserie. **[Presisert 2026-08-31]** «Øvre grense» er TRUKKET i manus (§ 13.13(b)): 15 bo med utfall er ennå ikke slettet, så testen bærer fravær av *systematisk* underfangst, ikke et tak på enkeltstående tapte utfall. Formuleringen her står som historikk og skal ikke gjeninnføres i publiseringsvendt tekst |
| G7 | L1 målt på utfallsserien | 1 441 av 9 979 innstillinger (14,4 %) mangler åpning i korpuset; 1 631 åpnet før vinduet | kohort-20 + kontroll-01 (eksakt) | Derfor bygges kohorten fra åpningssiden |
| G8 | Sensus på åpningsraden (kohorten) | bransje, tingrett, saksnr, bostyrer, fristdag: **5 165/5 165 (100 %)**; kapital 0/5 165 (død kolonne) | kohort-40 + kontroll-01 (L5-korrekt) | |
| G9 | De åpne boene er rene | de 351 har INGEN annen insolvenshendelse etter åpningen (ingen sletting, ingen fortsettelse) | kontroll-01 | Styrker «fortsatt åpne»-etiketten |

## H — Ankere og historikk

| # | Anker | Status | Bruk |
|---|---|---|---|
| H1 | **Ot.prp. nr. 26 (1998-99), Del 4 punkt 1.1** («Behovet for endringer»), regjeringen.no id159514 **?ch=4** | **VERIFISERT av kontrolløren 2026-08-30** — eksakt setning: «I 1996 ble således så mange som tre av fire boer innstilt av denne grunn, mens tallene i 1976 var to av fem boer.» Samme passasje bærer § 135 og pantelov-1980-forklaringen | Det historiske ankeret OG § 135-definisjonen. SITER «Del 4 punkt 1.1» — aldri «kap. 1.1» (briefen) eller «kap. 4». Lane 1s UBEKREFTET-nedgradering skyldtes at ?ch=4 ikke ble prøvd |
| H2 | De tre kohort-sammenliknbare målepunktene 1976 → 1996 → 2024 | **40 % → 75 % → 75,5 %** | 1976/1996 fra H1 (VERIFISERT); 2024-punktet er kohorten. INGEN egen tidsserie fra vårt materiale (L1). **Fila er omdøpt og utvidet 2026-08-30:** `figurer/historisk-maalepunkter-2026-08-30.csv` (sha256 `99bcbc1d98f333eea360aace9c4ceb6692398d3fdecf0f50df0dfaf4fe62d3bc` etter at verifikasjonen 2026-08-30 la til Prop. 56 L-raden, 23 rader) erstatter `historisk-trepunktslinje-2026-08-30.csv`. Kun disse tre radene har `plottes=ja`; H14–H18 og H22 står som kontekstrader med `plottes=nei` |
| H3 | SSB Opna konkursar (statistikkside) | VERIFISERT: 950 åpninger 2026K2, bygg 237; ingen utfallsdimensjon | Skala + hullet vi fyller |
| H4 | SSB Om statistikken (konkurs) | VERIFISERT: kilde Konkursregisteret; dekker kun opna konkursar | Beviser hullet |
| H5 | SSB API 09122 og 07165 | VERIFISERT ved egne API-kall (kontroll-04): 09122 2026K2 = 950/237 | Kalibreringen (G3–G5) |
| H6 | Brønnøysundregistrene, kunngjøringstyper fra Konkursregisteret | VERIFISERT: åtte typer inkl. innstilling/avslutning/fortsettelse; «available on the same day» | Lisensen for kunngjøringsdato som hendelsesdato |
| H7 | Forbrukerrådet-sitatet | VERIFISERT ordrett (avsnittet «Kva gjer du når seljar går konkurs?») | Forbrukerrammen |
| H8 | SSB Klass v30/v3218 + korrespondanse 2919; SN2025-innføring 01.09.2025 (820→736 koder; gradvis i statistikkene 2026–2029) | VERIFISERT | L17-håndteringen |
| H9 | Domstolsreformen: 59→23 rettskretser **26. april 2021** | VERIFISERT — datoen står på **snl.no/tingrett** (ikke på snl.no/domstolsreformen, som kun sier «våren 2021») | Siter snl.no/tingrett for datoen |
| H10 | Elleve nye tingretter fra 10. juni 2025 (seks delt) | VERIFISERT (domstol.no) | Forklarer navnebyttene på utfallsradene (E1) |
| H11 | konkursradet.no | **UBEKREFTET** (HTTP 403, bekreftet på nytt) | Siteres ALDRI; § 135 dekkes av H1 |
| H12 | Lønnsgarantiloven § 1 første ledd (i metodeboksens § 135-presisjon) | **VERIFISERT 2026-08-30** — sitatet bekreftet ordrett i to uavhengige oppslag av tallrevisjonen: lovdata.no/lov/1973-12-14-61 og paragrafsiden. Lovteksten begynner «For betaling …» — siteres «[f]or betaling …» ved liten forbokstav | Metodeboksens halvsetning står; anker = referanse 11 i manus (renummerert av verifikasjonen 2026-08-30) |
| H13 | SSB tabell 12972 (ukestatistikk, nevnt i briefen) | Ikke verifisert av noen lane | Ikke i bruk — utelat eller verifiser før bruk |
| H14 | **Ot.prp. nr. 23 (2003-2004) kapittel 2**, regjeringen.no id176709 **?ch=2** | **VERIFISERT ordrett 2026-08-30** i to uavhengige lesninger (departementets egen PDF + regjeringen.no HTML): «Det finnes for tiden ikke nøyaktig statistikk over hvor mange av de åpnede konkursboene som blir innstilt etter kkl. § 135.» + «Tallet på innstilte boer kan også omfatte konkursboer som er åpnet før …» + råtallene 4 445 / 2 767 (2002) og 2 652 / 849 / 1 691 / 524 (1H2003) | **Ankeret i den korrigerte nyhetspåstanden.** Kildens tall, aldri våre målinger |
| H15 | **Ot.prp. nr. 23 (2003-2004) punkt 7.1**, **?ch=7** | **VERIFISERT ordrett 2026-08-30**: «utgjør 75–80 prosent av avslutningene»; 3 577 (2000), 3 005 (1999); åpningstabell 1997–2000 per 31/12 = 3 689 / 3 726 / 4 375 / 5 116 | Nevner = AVSLUTNINGER, ikke åpninger. LANDMINE: passasjen ligger i kap. 7, ikke kap. 2 — den ble oversett i første søk |
| H16 | **Ot.prp. nr. 23 (2003-2004) punkt 16.2**, **?ch=16** | **VERIFISERT ordrett 2026-08-30**: ca. 53 % av oppbudsboene og 77 % av de skattefogdbegjærte boene er innstillingsbo; ca. 25 % begjært av skattefogden | Offentlig belegg for oppbud-hypotesen (E-kapitlet / kapittel 9). **LANDMINE: URL-en er ?ch=16, ikke ?ch=17** — ?ch=17 er «Merknader til lovforslaget» og bærer ikke passasjen. Undergruppeandeler, udatert innsamling, aldri sammenliknbar med A2 |
| H17 | **Mjøs, Kostøl og Pelja (2021), tabell 4 panel E** | **VERIFISERT ordrett 2026-08-30** i rapportens PDF-fulltekst: «hele 18 345 (89.9%) av sakene i utvalget avsluttes» pga. manglende midler, 2010–2019 | Nevner = AVSLUTTEDE saker i utvalget. Merk at kilden skriver 89.9% med punktum |
| H18 | **Justis- og beredskapsdepartementets høringsnotat 13.01.2023, saksnr. 23/251, punkt 9.4.3** | **VERIFISERT ordrett 2026-08-30** i høringsnotatets PDF-fulltekst: «data fra Brønnøysundregistrene viser at 90 prosent av alle konkursåpninger avsluttes på grunn av manglende midler» | Nyeste offisielle tallfesting — og den gjør selv nevnerfeilen: kilden (H17) regner av avslutningene |
| H19 | Brønnøysundregistrene, Statistikk fra Konkursregisteret | **VERIFISERT 2026-08-30**: kun «Konkursåpninger og tvangsavviklinger» 2018–2026 (fylke, periode); ingen utfallsdimensjon; sist oppdatert 03.08.2026 | Registerholderen fyller ikke hullet |
| H20 | SSB Historisk statistikk kap. 11 | **VERIFISERT 2026-08-30**: eneste konkurstabell er «Åpnede konkurser. 1887-1998» | SSBs avgrensning bakover til 1887 |
| H21 | **Byggsikt-risikostudien**, byggsikt.no/rad/konkursrisiko-norske-smaforetak/ | Byggsikts egen publiserte studie, 29.08.2026, foreløpig valideringsstudie v1.0. Live-URL svarer ikke på automatiserte oppslag (kjent og forventet); innhold og tall kontrollert mot publikasjonens kildefil 2026-08-30: 375 688 selskaper, 8 082 utfall, ROC-AUC 0,883, AP 0,411, topp 1/5/10 % = 29,10/55,85/67,03 % | Faglig komplement (før mot etter), sitert i kapittel 1 og 14 + referanse 10 i manus. **Skal ALDRI omtales som kalibrert, som ferdig sannsynlighet eller som kredittbeslutningsgrunnlag** — studien avviser alle tre selv («Kalibrering-i-det-store feilet»; «det absolutte nivået vurderes separat mot forhåndsdefinerte kalibreringsporter i kapittel 8, og bestod ikke» — begge verifisert ordrett i kildefila av verifikasjonen 2026-08-30) |
| H22 | **Prop. 56 L (2025–2026) punkt 2.6.2 «Funn og anbefalinger i rapporten»**, regjeringen.no id3154758 **?ch=2** | **VERIFISERT ordrett 2026-08-30** (verifikasjonen): «I analysen vises det til at data fra Brønnøysundregistrene viser at 90 prosent av alle konkursåpninger avsluttes på grunn av manglende midler.» Tilråding 27.03.2026; loven sanksjonert 19.06.2026 (LOV-2026-06-19-48, Lovdata LTI). **LANDMINE: proposisjonen nevner aldri «§ 135»** — et søk på paragrafnummeret alene finner den ikke | Den SENESTE offisielle tallfestingen; referanse 7 i manus. Gjentar H18s åpningsnevner mens kilden (H17) regner av avslutningene. Erstatter «sist i 2023» |
| H23 | Konkursrådet, «Gir bobehandlingen resultater?» (Reusch 1998) — sekundærspor | **UBEKREFTET** (nettsted nedlagt; speil ute av DNS; Wayback nede; konkursradet.no HTTP 403 — alt reprodusert av verifikasjonen 2026-08-30). Søkeindeksens rester tyder på: utvalg av bo AVSLUTTET fra 01.01.1993 ved Hedmark og Sunnmøre (156 + 180 bo), forskjeller mellom embetene i tid åpning→avslutning og i andel bo til utlodning | Siteres ALDRI som belegg. Er grunnen til at nedbrytnings-førstheten er formulert for det kohortmålte tallet (bruksregel 11); omtalt uten tall i kapittel 13.12 |
| H24 | **Oslo tingrett — årsmelding 2022, «Konkurs»** (domstol.no) | **VERIFISERT 2026-08-30**: «I 2022 var gjennomsnittlig saksbehandlingstid 284 dager»; 683 åpnede konkurser (2022); mål om 75 % ferdigbehandlet innen ett år. Ingen utfallsdimensjon, ingen sammenlikning mellom domstoler | Referanse 24 i manus — eksempelet i kapittel 3 på at én domstol publiserer egne varighetstall; begrunner at kapittel 3 sier «ingen offisiell statistikk», ikke «ingen offentlig kilde» |

### H-avledninger: egne divisjoner av kildens råtall (IKKE studiens målinger)

Disse fem tallene er utført av oss på H14/H15s råtall, med studiens avrundingsregel. De inngår **ikke** i noe
estimat, noen tabell eller noen figur, og skal aldri siteres som studiens tall. De står i kapittel 10 som
demonstrasjon av hva nevneren gjør.

| Periode | Regnestykke | Resultat | Merknad |
|---|---|---:|---|
| 2002 | 2 767 / 4 445 | **62,2 %** | Praktisk talt lik vår egen naive, ikke-modningskorrigerte andel (F4: 62,4 %) — som studien selv beviser er feil |
| 1999 | 3 005 / 4 375 | 68,7 % | Under kildens egen avslutningsandel (75–80 %) |
| 2000 | 3 577 / 5 116 | 69,9 % | Under kildens egen avslutningsandel (75–80 %) |
| 1. halvår 2003, konkurser | 1 691 / 2 652 | 63,8 % | |
| 1. halvår 2003, samlet | 2 215 / 3 501 | 63,3 % | Konkurser + tvangsavviklinger i begge ledd |

### Korrigert nyhetspåstand (2026-08-30)

**STRØKET:** «Tallet er ikke oppdatert offisielt siden 1996» / «lukker et tretti år gammelt hull» /
«den første moderne oppdateringen av et tall som sist ble offentlig tallfestet for 1996». Påstanden er
uriktig — H14, H15, H17 og H18 tallfester alle andelen eller antallet etter 1996.

**GJELDENDE:** studien er den første som måler utfallet for en **avgrenset åpningskohort** av konkursbo,
fulgt til utfall med høyresensureringen målt, og den første som bryter **det slik målte tallet** ned på
byggfag og rettskrets. Begrunnelsen er nevneren: hver tallfesting i litteraturen er enten et råtall per
kalenderår, en andel av de allerede avsluttede boene, eller en undergruppeandel etter rekvirenttype.
Departementet skrev begrensningen selv i 2003 (H14). **Rettelsen flyttet ingen målte tall** — A-, B-, C-,
D-, E-, F- og G-seriene står urørt.

*Verifikasjonens tillegg (2026-08-30, samme dag):* den første rettelsens formulering «sist av
Justis- og beredskapsdepartementet i 2023» ble angrepet på nytt og falt — Prop. 56 L (2025–2026)
gjentar 90-prosenttallet 27.03.2026 med samme åpningsnevner (H22; proposisjonen nevner aldri «§ 135»,
derfor slapp den gjennom det første søket). Manus, metodegrunnlag.json, figurgrunnlaget (ny sha i H2)
og referanselisten (nå 29 referanser; Prop. 56 L = nr. 7, Oslo tingrett = nr. 24, Byggsikt = nr. 10)
er oppdatert. Nedbrytnings-førstheten er samtidig presisert til det kohortmålte tallet (H23), og
kapittel 3 sitt «ingen offentlig kilde» er skjerpet til «ingen offisiell statistikk» med
Oslo tingrett-eksemplet (H24). Fortsatt ingen målte tall flyttet.

---

## I — Fagfellerevisjonen 2026-08-31 (nye tall)

Alle tall i denne seksjonen er beregnet på det **frosne kohortuttrekket**
(`data/_kohort-rader-arbeidskopi.json`), ikke mot databasen, slik at de er knyttet til
nøyaktig samme kohort som A–G. Skriptene er `sporringer/rev2-02..09*.mjs`; utfallsfilene
`data/rev2-0X-*-2026-08-30.json` er verifisert byte-deterministiske over to kjøringer.
Biblioteksvalideringen `rev2-01` kjører 26 assertsjoner mot denne talljournalen: 0 feil.

| # | Tall | Verdi | Kilde | Forbehold |
|---|---|---|---|---|
| I1 | **PRIMÆRESTIMAT: 24-mnd kumulativ insidens for § 135** | **alle 74,82 %** [73,60–75,99], risikomengde 292; **bygg 70,54 %** [67,93–72,98], rm 89; **øvrige 76,23 %** [74,85–77,55], rm 203 | rev2-02 | Aalen–Johansen, ordinær avslutning som konkurrerende hendelse; deltametode-varians, log(−log)-KI. Grenseregel for de 3 randtilfellene gir 74,88 %. Publiseres med én desimal: 74,8 / 70,5 / 76,2 |
| I1b | CIF ved 12 og 18 mnd | 12 mnd 63,18 / 57,11 / 65,17 %; 18 mnd 71,89 / 66,87 / 73,54 % (alle/bygg/øvrige) | rev2-02 | Risikomengder 1 478 og 768. Alle 5 165 bo har ≥ 601 dagers oppfølging, så ved 12 og 18 mnd er AJ **eksakt lik** rå andel — ingen sensurering i vinduet |
| I1c | Antakelsesfri kontroll av 24-mnd (delkohort med full oppfølging) | **2 810/3 772 = 74,50 %** [CP 73,07–75,88]; bygg 653/934 = 69,91 %; øvrige 2 157/2 838 = 76,00 % | rev2-02 | **Dette er F1/F2 ved 24 mnd** — samme nevnere; tellerne avviker med ett bo per gruppe mot kohort-20 (2 812/654/2 158), se F2-noten. F1/F2 er altså delkohort-estimatoren, ikke Aalen–Johansen. Begge er gyldige fasthorisont-tall; differansen mot I1 (0,3 pp) er prisen for ulik nevner. Skal stå i metodefila så de ikke leses som uenighet |
| I2 | **Grays test, bygg mot øvrige** | z = −5,671; χ²(1) = **32,157**; **p = 1,42×10⁻⁸** | rev2-03 | Gray (1988), ρ = 0, på subdistribusjonsrisikomengden. Grenseregel gir z = −5,649, p = 1,61×10⁻⁸. **Primær gruppekontrast** (bruksregel 12) |
| I2b | **Risikodifferanse bygg − øvrige ved 24 mnd** | **−5,70 pp** [−8,56; −2,83]; z = −3,902, p = 9,5×10⁻⁵; RR 0,9253 [0,8891; 0,9630] | rev2-03 | Praktisk talt identisk med as-of-differansen −5,69 pp [Newcombe −8,54; −2,92]. **Si det eksplisitt** — det viser at estimatorbyttet ikke endrer funnet |
| I2c | Risikodifferanse ved 12 og 18 mnd | 12 mnd −8,06 pp [−11,16; −4,97], p = 3,4×10⁻⁷; 18 mnd −6,66 pp [−9,59; −3,74], p = 8,2×10⁻⁶ | rev2-03 | Differansen KRYMPER over tid (−8,1 → −6,7 → −5,7). Samme signal som PH-bruddet: byggforskjellen er TIDLIG, ikke vedvarende |
| I3 | **CIF-medianer med KI** | bygg **267 d** [testinversjon 245–302; bootstrap 245–304], rm 565; øvrige **205 d** [196–217 begge], rm 1 820; **differanse +62 d** [bootstrap 36–98] | rev2-04 | Brookmeyer–Crowley-inversjon + 2 000 bootstrap (mulberry32, frø 20260830). **I3 og D5 er ULIKE ESTIMANDER** — D5 sammenliknes med rå +34,5, aldri med +62 (bruksregel 12) |
| I4 | Hasardratio med KI | se D6 | rev2-04 | |
| I5 | **PROPORSJONALITETSANTAKELSEN FORKASTES** | Grambsch–Therneau χ²(1) = **20,32**, p = **6,57×10⁻⁶** (rangtransform); 19,48, p = 1,02×10⁻⁵ (log). 3 894 hendelser | rev2-04 | Scoretest på Schoenfeld-residualene fra den stratifiserte Cox-modellen. **KREVER at ordet «vedvarende» aldri brukes om HR 0,80** |
| I5b | **Tidsdelt hasardratio** | dag 0–180: **HR 0,706** [0,643; 0,776], 2 251 hendelser; 180–365: 0,927 [0,807; 1,065]; 365–730: 0,982 [0,818; 1,178]; 730+: 0,902 [0,464; 1,751] | rev2-04 | Substansielt funn, ikke bare diagnostikk: **alle intervaller etter dag 180 dekker 1**. Hele byggforskjellen ligger i de første seks månedene |
| I6 | **Holm-korrigerte domstolskontraster** | **3 av 120 par** overlever: Hordaland mot Møre og Romsdal (p_Holm 0,0031), Oslo (0,0056), Trøndelag (0,0056). 19 av 120 signifikante ukorrigert | rev2-06 | Fisher eksakt + Holm–Bonferroni. «Én krets mot resten»: Hordaland eneste som skiller seg (p_Holm 0,0012); Møre og Romsdal faller (0,178) |
| I7 | **Differensielle vippepunkter for de 351 uavgjorte** | ved x_Ø = 0 % kreves **65,6 %** i bygg (73 av 111); ved 25 % kreves **83,4 %** (93 av 111); ved 50 % **umulig**. Eksakt umulighetsgrense **x_Ø > 48,3 %** (116 av 240) | rev2-05 | Erstatter felles-x-sensitiviteten som eneste analyse. B9s krysningspunkt x = 2,28 står, men beviser bare at ingen FELLES rate kan snu rekkefølgen |
| I7b | Verste tilfelle | bygg 1 022/1 280 = **79,84 %** mot øvrige 2 986/3 885 = 76,86 %; +2,98 pp [Newcombe 0,36; 5,49] — **rekkefølgen SNUR** | rev2-05 | Skal publiseres. Forskjellen slutter å være signifikant ved 39 av 111 (Fisher p = 0,058); snur ved 73 av 111 |
| I7c | **Empirisk anker (nytt, ikke etterspurt)** | eventuell § 135-rate blant uavgjorte bo: bygg **37,7 %** [32,3–43,3] mot øvrige **41,6 %** [38,1–45,2]; differanse −3,87 pp [Newcombe −10,14; 2,61], Fisher **p = 0,246**. To andre vinduer: p = 0,487 og p = 0,365 | rev2-05 | Landemerkeanalyse av bo uavgjorte ved dag L med FULL oppfølging til L+Δ (ingen sensurering i vinduet). Raten er statistisk uskillbar mellom gruppene — hvis noe LAVERE i bygg. Verste-fall-scenariet ligger langt utenfor det materialet støtter |
| I8 | Standardisering, utvidet | se E6 | rev2-07 | Stratatabell med 45 bøtter n ≥ 10 + samlerad for 29 små (125 bo), og per-krets O/E med KI og vektgrunnlag, ligger i utfallsfila og skal publiseres i metodefila |
| I9 | **Permutasjonstest, 100 000 omstokkinger** | 0 av 100 000 nådde observert verdi; permutasjons-p = **1,0×10⁻⁵** = oppløsningsgrensen 1/(B+1); største \|z\| i nullfordelingen 4,759 | rev2-08 | Byggmerket omstokket INNENFOR hver rettskrets (Fisher–Yates, mulberry32, frø 20260830). Den asymptotiske p-verdien 8,9×10⁻¹⁰ ligger **4,1 tierpotenser** under oppløsningsgrensen — en permutasjonstest kan ALDRI bekrefte den direkte |
| I9b | Hva permutasjonstesten faktisk validerer | nullfordelingens kalibrering: snitt 0,0033 (0), sd 1,0033 (1), skjevhet 0,0245 (0), kurtose 2,979 (3); KS D√B = 0,818, p = 0,515; halefrekvenser 5,041 / 1,000 / 0,091 / 0,007 % mot 5 / 1 / 0,1 / 0,0063 % | rev2-08 | **Den forsvarlige formuleringen:** testen validerer REFERANSEFORDELINGEN, som er nettopp antakelsen den asymptotiske p-verdien hviler på. Grays test tilsvarende (20 000 omstokkinger, snitt −0,0033, sd 1,0006, 0 ekstremer) |

**IKKE KJØRT (skal fortsatt stå som ikke kjørt i § 13.8):** Fine–Gray-regresjon på
underfordelingshasarden (bevisst — kunne ikke valideres mot en referanseimplementasjon i
dette miljøet); Cox med flere kovariater samtidig; klynget bootstrap for hovedandelene
(klynge-robust SE er beregnet for HR som delvis erstatning); de fire tilleggene til
slettingskontrollen i § 12.2.

**NY DATABASEDEFEKT MELDT, IKKE FIKSET:** `kontroll-05-kanonisk-stat.mjs` joiner mot
åpningskunngjøringen uten deduplisering på orgnr. Ett foretak har to åpningsrader på samme
dato og telles dobbelt — kontroll-05 arbeider med 5 166 rader, ikke 5 165. Påvirker bare
kontroll-05s egne avledede tall (D5), ikke kohortens kjernetall, som bygges fra en
deduplisert kohorttabell. Føres til MÅ-FIKSES punkt 10.

### Kildeavgjørelser 2026-08-31 (fagfellerevisjonen)

Verifisert mot primærkilde; full dokumentasjon i `kilder/REVISJON-KILDER.md`.

| # | Funn | Status | Konsekvens |
|---|---|---|---|
| K1 | **Ot.prp. nr. 26 (1998-99) Del 6 punkt I.1** identifiserer 1976–1991-serien som statistikk over AVSLUTTEDE konkurser, hentet fra NOU 1993: 16 s. 133, og beskriver nevneren ordrett som § 135-bo mot § 128-bo | BEKREFTET (?ch=6) | Figurtekst 1 og § 13.13(c) rettet. 1976-punktet er BEVISELIG en avslutningsandel; påstanden om «de eneste sammenliknbare i form» er svekket. Referanse 1 utvidet med Del 6 |
| K2 | Nevner-inkonsistensen er INTERN i Mjøs m.fl. (2021): brødteksten sier utvalget «består av alle avsluttede reelle konkursåpninger», narrativet sier «90 prosent av alle konkursåpninger». Korrekt åpningsandel = 18 345/33 762 = **54,3 %** | BEKREFTET (PDF sha256 38e4668…) | Kapittel 1 og sammendraget tilskriver nå glidningen til rapporten selv |
| K3 | Ot.prp. nr. 23 punkt 16.2: **oppbud 53 %, lønnstaker 80 %, skattefogd 77 %, skatteoppkrever 85 %**; ingen sats for private fordringshavere (bare «under 5 % av boene») | BEKREFTET | Bruksregel 14. Mekanismesetningen i kapittel 9 slettet |
| K4 | Klass-endepunkt 2919 har **241 identitetsrader**, men **220 av 738 SN2025-koder mangler helt**; SSBs Excel (29.04.2026) har 1 251 kodepar og bare 3 hull. Klass har kun ÉN tabell, SN2025 → SN2007 — studien bruker riktig retning | DELVIS AVKREFTET / DELVIS BEKREFTET | Kapittel 11.4-kulepunktet og referanse 20 omskrevet med versjon, dato og avtrykk |
| K5 | Korrespondansetabellen er revidert **seks ganger på fjorten måneder**; revisjonen 14.04.2026 splittet 43.220 i 43.221/222/223 — koden for Rørleggerarbeid (n = 83) | BEKREFTET | Kohortvinduet er upåvirket (SN2007-periode), men reproduserbarhet krever dato og versjon |
| K6 | «Hele differansen er enkeltpersonforetak» er **92,3 %**, ikke 100: 1 530 av 1 658; øvrige 128 er NUF (54), Andre (70), ANS (4) | AVKREFTET | Kapittel 12.1 og § 13.4 rettet |
| K7 | «820 til 736 koder» gjengir SSBs prosa korrekt, men byråets Klass-artefakt gir **738** | BEKREFTET | Fotnote i kapittel 12.1; tallet 736 beholdes som byråets egen formulering |
| K8 | Brønnøysund kunngjør utfall enkeltvis (FOR-1993-08-23-824 § 18; åtte kunngjøringstyper, typene 6–8 = våre tre utfall). Det som mangler, er et **kohortkoblet aggregat** — ni av ni SSB-tabeller teller åpninger | BEKREFTET | «Står ingen steder» erstattet i kapittel 1. Manuskriptets «åtte hendelsestyper» i kapittel 3 er EKSAKT riktig og skal ikke endres |
| K9 | SSB 2026K2: alle opna 950 (bygg 237); foretakskonkurser ekskl. ENK 930; ENK inkl. personlige 20. **Begge parter har rett** — manuskriptets 950/237 er raden for alle opna | BEKREFTET | Kapittel 1 oppgir nå hvilken rad tallet er hentet fra |
| K10 | AS + ASA = **11 132 av 12 790** åpninger 2023K3–2026K2 = **87,0 %**. 11 174/11 132 = 100,377 %; 11 174/12 790 = 87,365 % | BEKREFTET mot SSB API | Begge kalibreringsnevnere nå UAVHENGIG reprodusert. Tittelavgrensningen til AS/ASA er kvantifisert |
| K11 | **FELLE for neste agent:** Brønnøysunds «available … for three weeks» står under overskriften om OPPHEVING (lagmannsrettens opphevelse), ikke om innstilling/avslutning | — | Kan verken brukes for eller mot retensjonsargumentet |
| K12 | NOU 1993:16 s. 133 er IKKE hentet direkte | ÅPENT | Alle formuleringer sier «proposisjonen identifiserer …», aldri noe om NOU-ens egen konstruksjon |

---

## MÅ-FIKSES før publisering

> **STATUS 2026-08-30 (sluttredaksjonen):** 1 UTFØRT (kohort-10-frys peker nå på den
> kanoniske kaskaden + kart v3; refrosset sammendrag reproduserer 1 280/1 411/155 eksakt;
> kryssjekken i skriptet feiler hardt ved avvik). 2 UTFØRT (alle publiseringsfiler
> reassemblert etter oppskriften — to utfallskolonner ≥ 10, domstolstabell kun n ≥ 100,
> byggsplitten for Nord-Troms og Senja strøket, uoppgitt = 155-bøtta; assertert kvittering i
> `data/sluttred-reassemblering-2026-08-30.json`). 3 UTFØRT (alle lane-referanser vasket ut av
> filene i data/ og figurer/ samt domstol-ankere.json; kontrollørens egen frosne
> `kontroll-kjerne-2026-08-30.json` står urørt som forseglet arbeidsdokument). 4 IVARETATT
> (begge merknader står i figur 6-teksten; 2026K3 strykes). 5 IVARETATT (briefen har fått
> varselbanner som peker hit; historiske verifikasjonsutsagn i briefen omskrives ikke).
> 6 UTFØRT (historikkfila står som VERIFISERT; omdøpt og utvidet 2026-08-30, se H2). 7 UTFØRT (foreldet
> `sporringer/bransjeklassifikator.mjs` slettet). 8 UTFØRT (H12 verifisert, se raden).
> 9 IVARETATT (flagget i v3-kartet ignoreres; byggflagg beregnes alltid av koden — dokumentert
> i kohort-10-frys og sluttred-01). 10 STÅR (databasefunn eies av andre; meldt, ikke fikset).
> I tillegg: figurgrunnlaget `domstol-modningskurve-cif.tsv` er regenerert på kanonisk
> byggdefinisjon (var utgått definisjon, 1 142; ga 56,7/65,0 ved ett år der manus siterer
> 57,2/65,2 — nå reproduserer fila D3/D4 eksakt), og byggandel-kolonnen i
> `domstol-punktdiagram.tsv` er regenerert på primærdefinisjonen (spenn 15,7–34,8, jf. E7).

1. **Refrys kohortsammendraget på v3-kartet.** `kohort-10-frys.mjs` leser
   `bransjekart-v2.json`; det frosne `data/kohort-sammendrag-2026-08-30.json` bærer
   derfor bygg 1 270/1 401 (mangler «Blikkenslagerarbeid på tak», 10 bo) og en
   uklassifisert-bøtte på 226. Kanonisk er 1 280/1 411
   (`data/kohort-hovedtall-2026-08-30.csv`, bekreftet av to klassifikatorer + kontrollør).
   Pek frysen på v3 og kjør på nytt — ellers har artikkelen to byggnevnere i egne filer.
2. **Minstecelle-regelen brytes i dagens publiseringsfiler.** `PUBLISERBAR-per-bransje`,
   `PUBLISERBAR-per-tingrett`, `PUBLISERBAR-bygg-per-tingrett`, `F1-byggfag`,
   `bransje-kohortaggregat-A` og `kohort-per-bransje/-tingrett` har celler < 10 i
   kolonnene innstilt/avsluttet/åpne. Reassembler de publiserte tabellene slik:
   (a) to utfallskolonner — **innstilt** og **ikke innstilt** — begge ≥ 10, ellers til
   restrad; (b) domstolstabellen kun n ≥ 100 (alle celler ≥ 22); (c) i
   bygg-per-tingrett strykes byggsplitten for Nord-Troms og Senja (ikke-innstilt = 6);
   (d) uoppgitt publiseres som 155-bøtta (B10). Aggregatkuben
   (`kohort-aggregatkube`) er allerede regelrett.
3. **Vask figurfilhoder som skipper:** `figurer/domstol-*.tsv` sier «lane 3» i
   kommentarhodet — fjern all intern arbeidsorganisering; behold formuleringen
   «offentlig tilgjengelige registerkunngjøringer».
4. **Figurtekster:** i den naive kvartalskurven dekker «2023K3» kun september (327
   åpninger — vinduet starter 2023-09-01), og 2026K3 er et delkvartal (til 2026-08-24)
   — begge må merkes eller strykes; 2026K3 anbefales strøket.
5. **Rett briefens tekst:** 75,4 → 75,5; byggtallene (B); «≥ 20 mnd» → A6;
   seriestartene → F5; Ot.prp.-siteringen → H1; domstolsspennene → E3/E4.
6. **Oppdater statuskolonnen** i historikkfila (UBEKREFTET → VERIFISERT, med H1-referansen).
   *Etterskrift 2026-08-30:* fila er dessuten omdøpt og utvidet til
   `figurer/historisk-maalepunkter-2026-08-30.csv` som følge av rettelsen av
   nyhetspåstanden — se H2 og H14–H21. Den gamle `historisk-trepunktslinje-2026-08-30.csv`
   er fjernet; begge dens plottbare punkter er videreført uendret.
7. **Slett foreldet skript:** `sporringer/bransjeklassifikator.mjs` er lane 1s
   forlatte kopi (erstattet av `kohort-bransjeklassifikator.mjs`) — fjern for å unngå
   at en fjerde part importerer feil modul.
8. **Hent H12-ankeret** (lønnsgaranti) eller stryk halvsetningen i metodeboksen.
9. **Post-søm-serier:** enhver byggserie som krysser 2025-09-01 må deklarere
   håndteringen av SN2025-etiketten «Utvikling og salg av byggeprosjekter» (68.120 ↔
   SN2007 41.101/41.109/42.990). v3-kartet flagger den i dag som `er_bygg_kjerne=true`
   — i strid med kjernedefinisjonen (0 effekt på kohorten, som er før sømmen).
10. **Databasefunn til eierne (IKKE fikset her):** (a) 3 406 rader har «Kjennelse
    avsagt:» limt inn i saksnr (52 med ødelagt domstolskode); (b) 98 rader har
    flerlinjet bransje; (c) «Enheten er slettet» lekket inn i bransjefeltet på 9
    foretak; (d) `docs/database/05-livslop.md` er stale (seriestarter én dag feil i
    JS-lesning; «har tingrett»-tabellen utelater avslutningsraden der tingrett er 0 %
    utfylt men bostyrer 100 %); (e) L16-forurensningen i `company_intel.livslop` —
    IKKE brukt av noen lane i denne studien (verifisert ved lesning av samtlige
    spørringsfiler); (f) **[2026-08-31]** `kontroll-05-kanonisk-stat.mjs` joiner mot
    åpningskunngjøringen uten deduplisering på orgnr — ett foretak har to åpningsrader på
    samme dato, så skriptet arbeider med 5 166 rader. Påvirker kun kontroll-05s egne
    avledede tall (D5), ikke kohortens kjernetall.
11. **[2026-08-31] Publiseringsfiler som må regenereres etter fagfellerevisjonen:**
    (a) `figurer/domstol-punktdiagram.tsv` trenger en kolonne med den sensureringsbevisste
    CIF-medianen per krets (spenn 133–322 dager), som nå er figur 5s vannrette akse;
    (b) `figurer/historisk-maalepunkter-*.csv` bør få nevnertypen «avsluttede konkurser
    (§ 135 mot § 128)» på 1976-raden og Del 6 punkt I.1 som kildefelt (K1);
    (c) et nytt figurgrunnlag for kumulativ insidens ved 12/18/24 måneder med
    risikomengder bør legges ved hovedtallblokken;
    (d) **[2026-08-31, verifikasjonen]** `figurer/domstol-modningskurve-cif.tsv` bør
    regenereres fra det frosne uttrekket under den kanoniske utfallsregelen: dagens fil
    bærer den databaserte veiens én-bo-avvik ved ett år (57,2 % der manus og I1b nå
    siterer 57,1 %), jf. D4-noten. Ingen av de fire er gjort her.

*Satt og signert av datakontrolløren, 2026-08-30. Kontrollspørringer:
`sporringer/kontroll-01..05*.mjs`. Frosset kontrollresultat:
`data/kontroll-kjerne-2026-08-30.json` (sha256
`ba0a85ab27774c0b5a7d0bcdd92c47605269e01cee571a009a80c2190de3f3c8`).*

*Seksjon I, bruksreglene 12–16, kildeavgjørelsene K1–K12 og MÅ-FIKSES-punkt 11 er lagt til
2026-08-31 etter den eksterne fagfellevurderingen (rapporten er ikke tatt med i dette depotet;
kildedokumentasjon i `kilder/REVISJON-KILDER.md`). Revisjonsspørringer:
`sporringer/rev2-01..09*.mjs`; frosne utfall `data/rev2-0X-*-2026-08-30.json`, verifisert
byte-deterministiske over to kjøringer med sha256 oppgitt i `rev2-09-sammenstilling`.
Vakten mot de tolv låste kjernetallene passerte med 0 brudd, og de 26 assertsjonene i
`rev2-01-validering` mot denne journalen passerte alle. Ingen målt kjerneverdi er endret.*

*Adversariell sluttverifikasjon 2026-08-31: fagfellens 20 punkter + 3 tillegg kontrollert
ett for ett mot manus, primærkildene (`kilder/REVISJON-KILDER.md`,
`kilder/otprp-23-2003-2004-tekstuttrekk.txt`) og rev2-utfallsfilene. To gjenværende
estimandkollisjoner rettet i manus: D4s 57,2 % harmonisert til I1b (57,1 %, se D4-noten og
MÅ-FIKSES 11(d)), og «reprodusert eksakt»-formuleringen om F2 mot I1c nedjustert til «gjenskapt
til én desimal» (ett bo per gruppe skiller tellerne, brobygget i manus kap. 4/10 og § 13.9).
G6s «øvre grense» historikk-merket. Alle tolv låste kjernetall står uendret.*
