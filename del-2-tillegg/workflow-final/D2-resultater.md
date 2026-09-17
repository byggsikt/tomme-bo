# D2 — resultater (generert av D2-sjekkliste.py, 12.09.2026)

## 0. Kontroll mot verifiserte tall (må stemme før noe nytt regnes)

| Kontroll | D2 | Forventet (B2 / V-B2) |
|---|---|---|
| kohort / innstilt / avsluttet / åpne (as-of) | 5165 / 3897 / 917 / 351 | 5165 / 3897 / 917 / 351 |
| fullvindu n / innstilt ≤730 d / ord. avsl ≤730 d / åpne d730 | 3772 / 2812 / 670 / 290 | 3772 / 2812 / 670 / 290 |
| sum eiendeler 3 bånd + ingen (fullvindu): <1 / 1–5 / ≥5 / ingen | 1929 / 1006 / 583 / 254 | 1929 / 1006 / 583 / 254 |
| siste pliktige regnskap: levert / ikke levert / for ungt (fullvindu) | 2960 / 435 / 377 | 2960 / 435 / 377 |
| samme, alle 5 165 | 4014 / 667 / 484 | 4014 / 667 / 484 |
| Revisor-tilstand alle 5 165: ingen / navngitt / utgaar / tvetydig | 3151 / 1382 / 632 / 0 | 3151 / 1382 / 632 / 0 (V-B2-04) |
| egen avledning = V-B2-04 rad for rad | 5165 av 5165 | 5165 |
| B2s «har noen gang hatt revisor» (fullvindu) / derav Utgår som siste verdi | 1466 / 458 | 1466 / 458 |
| revisor navngitt ved åpningen (fullvindu) / ikke | 1008 / 2764 | 1008 / 2764 |
| B2s sjekkliste (gammelt flagg), n per 0/1/2/3 | 966 / 895 / 1327 / 584 | 966 / 895 / 1327 / 584 |
| B2s sjekkliste, innstilt ≤730 d % | 53.1 / 73.1 / 84.5 / 89.7 | 53.1 / 73.1 / 84.5 / 89.7 |
| B2s sjekkliste, median dager | 247 / 161 / 128 / 120 | 247 / 161 / 128 / 120 |
| B2s sjekkliste as-of n | 1294 / 1245 / 1838 / 788 | 1294 / 1245 / 1838 / 788 |
| revisor univariat (B2-flagg) med / uten | 891 / 1466 = 60.8 % / 1921 / 2306 = 83.3 % | 891/1466 = 60.8 / 1921/2306 = 83.3 |
| revisor univariat (korrigert) med / uten | 535 / 1008 = 53.1 % / 2277 / 2764 = 82.4 % | 535/1008 = 53.1 / 2277/2764 = 82.4 |

Tvetydige siste-dager (to ulike Revisor-verdier samme dag): 0 (strengt før) / 0 (t.o.m. åpningsdagen). Bo hvis tilstand endres når Revisor-felt datert på selve åpningsdagen telles med: 6 av 5 165 (1 blir «navngitt», 5 mister revisor).

Rad-for-rad mot B2-per-estate.csv: sum eiendeler-bånd like 5165/5165; leveringsstatus like 5165/5165; y730 like 5165/5165; «har hatt revisor» like 5165/5165.

## 1. Sjekklisten med korrigert revisorflagg

Flaggene: (1) sum eiendeler i siste balanse før åpningsåret under 1 mill. kr, eller ingen balanse; (2) INGEN revisor registrert ved åpningen (siste «Revisor»-felt på kunngjøringene før åpningen bærer ikke et navn — enten er feltet aldri kunngjort, eller siste verdi er «Utgår»); (3) siste pliktige årsregnskap ikke levert (godkjenning ikke kunngjort før åpningen), eller selskapet for ungt til å ha levert noe — samme definisjon som B2/V-B2.

### 1.1 Hovedtabell — korrigert flagg (revisor registrert ved åpningen)

Kun flagg (2) er endret mot B2/V-B2; flagg (1) og (3) er identiske.

| Flagg | n (730 d) | Innstilt innen 730 d | Wilson 95 % | Ordinært avsluttet ≤730 d | Fortsatt åpent dag 730 | Median dager til innstilling (innstilte ≤730 d) | AJ 730 d (alle 5 165) | n (as-of) | Innstilt as-of 24.08.2026 | Wilson 95 % | Ord. avsl. as-of | Åpne as-of | Median dager (innstilte as-of) |
|---|---:|---|---|---|---|---:|---|---:|---|---|---|---|---:|
| 0 | 792 | 387 / 792 = 48.9 % | [45.4–52.3] | 234 = 29.5 % | 171 = 21.6 % | 263 | 49.1 % | 1068 | 544 / 1068 = 50.9 % | [47.9–53.9] | 352 = 33.0 % | 172 = 16.1 % | 271 |
| 1 | 810 | 572 / 810 = 70.6 % | [67.4–73.7] | 180 = 22.2 % | 58 = 7.2 % | 195 | 71.1 % | 1103 | 789 / 1103 = 71.5 % | [68.8–74.1] | 229 = 20.8 % | 85 = 7.7 % | 201 |
| 2 | 1561 | 1307 / 1561 = 83.7 % | [81.8–85.5] | 208 = 13.3 % | 46 = 2.9 % | 126 | 84.2 % | 2168 | 1828 / 2168 = 84.3 % | [82.7–85.8] | 267 = 12.3 % | 73 = 3.4 % | 127 |
| 3 | 609 | 546 / 609 = 89.7 % | [87.0–91.8] | 48 = 7.9 % | 15 = 2.5 % | 119 | 88.9 % | 826 | 736 / 826 = 89.1 % | [86.8–91.1] | 69 = 8.4 % | 21 = 2.5 % | 120 |
| **Alle** | 3772 | 2812 / 3772 = 74.5 % | [73.1–75.9] | 670 = 17.8 % | 290 = 7.7 % | 149 | 74.9 % | 5165 | 3897 / 5165 = 75.5 % | [74.3–76.6] | 917 = 17.8 % | 351 = 6.8 % | 152 |

Differanse 3 mot 0 flagg: +40.8 pp [+36.4; +44.9] (730 d); +38.2 pp [+34.4; +41.7] (as-of). Univariat AUC for antall flagg (730 d): 0.701; χ²-test p = 1.1e-91.

### 1.2 Til sammenlikning — B2s gamle flagg («har noen gang hatt revisor», 458 strøkne telt som registrert)

Reproduksjon av B2 § 1.36b / 5.5 og V-B2 § 1 (skal være 966/895/1 327/584 og 53,1/73,1/84,5/89,7).

| Flagg | n (730 d) | Innstilt innen 730 d | Wilson 95 % | Ordinært avsluttet ≤730 d | Fortsatt åpent dag 730 | Median dager til innstilling (innstilte ≤730 d) | AJ 730 d (alle 5 165) | n (as-of) | Innstilt as-of 24.08.2026 | Wilson 95 % | Ord. avsl. as-of | Åpne as-of | Median dager (innstilte as-of) |
|---|---:|---|---|---|---|---:|---|---:|---|---|---|---|---:|
| 0 | 966 | 513 / 966 = 53.1 % | [50.0–56.2] | 272 = 28.2 % | 181 = 18.7 % | 247 | 53.2 % | 1294 | 707 / 1294 = 54.6 % | [51.9–57.3] | 403 = 31.1 % | 184 = 14.2 % | 250 |
| 1 | 895 | 654 / 895 = 73.1 % | [70.1–75.9] | 183 = 20.4 % | 58 = 6.5 % | 161 | 73.7 % | 1245 | 923 / 1245 = 74.1 % | [71.6–76.5] | 230 = 18.5 % | 92 = 7.4 % | 163 |
| 2 | 1327 | 1121 / 1327 = 84.5 % | [82.4–86.3] | 169 = 12.7 % | 37 = 2.8 % | 128 | 84.9 % | 1838 | 1564 / 1838 = 85.1 % | [83.4–86.6] | 217 = 11.8 % | 57 = 3.1 % | 128 |
| 3 | 584 | 524 / 584 = 89.7 % | [87.0–91.9] | 46 = 7.9 % | 14 = 2.4 % | 120 | 89.0 % | 788 | 703 / 788 = 89.2 % | [86.9–91.2] | 67 = 8.5 % | 18 = 2.3 % | 122 |
| **Alle** | 3772 | 2812 / 3772 = 74.5 % | [73.1–75.9] | 670 = 17.8 % | 290 = 7.7 % | 149 | 74.9 % | 5165 | 3897 / 5165 = 75.5 % | [74.3–76.6] | 917 = 17.8 % | 351 = 6.8 % | 152 |

Differanse 3 mot 0 flagg: +36.6 pp [+32.5; +40.5] (730 d); +34.6 pp [+31.0; +37.9] (as-of). Univariat AUC for antall flagg (730 d): 0.693; χ²-test p = 5.9e-81.

### 1.3 Sensitivitet — Revisor-felt datert på selve åpningsdagen teller med (dato ≤ åpning)

53 bo har et Revisor-felt datert på åpningsdagen; hovedvarianten teller bare felt strengt før åpningen (V-B2-04).

| Flagg | n (730 d) | Innstilt innen 730 d | Wilson 95 % | Ordinært avsluttet ≤730 d | Fortsatt åpent dag 730 | Median dager til innstilling (innstilte ≤730 d) | AJ 730 d (alle 5 165) | n (as-of) | Innstilt as-of 24.08.2026 | Wilson 95 % | Ord. avsl. as-of | Åpne as-of | Median dager (innstilte as-of) |
|---|---:|---|---|---|---|---:|---|---:|---|---|---|---|---:|
| 0 | 791 | 386 / 791 = 48.8 % | [45.3–52.3] | 234 = 29.6 % | 171 = 21.6 % | 264 | 49.2 % | 1064 | 543 / 1064 = 51.0 % | [48.0–54.0] | 349 = 32.8 % | 172 = 16.2 % | 273 |
| 1 | 811 | 573 / 811 = 70.7 % | [67.4–73.7] | 180 = 22.2 % | 58 = 7.2 % | 195 | 70.9 % | 1107 | 790 / 1107 = 71.4 % | [68.6–73.9] | 232 = 21.0 % | 85 = 7.7 % | 200 |
| 2 | 1561 | 1307 / 1561 = 83.7 % | [81.8–85.5] | 208 = 13.3 % | 46 = 2.9 % | 126 | 84.2 % | 2168 | 1828 / 2168 = 84.3 % | [82.7–85.8] | 267 = 12.3 % | 73 = 3.4 % | 127 |
| 3 | 609 | 546 / 609 = 89.7 % | [87.0–91.8] | 48 = 7.9 % | 15 = 2.5 % | 119 | 88.9 % | 826 | 736 / 826 = 89.1 % | [86.8–91.1] | 69 = 8.4 % | 21 = 2.5 % | 120 |
| **Alle** | 3772 | 2812 / 3772 = 74.5 % | [73.1–75.9] | 670 = 17.8 % | 290 = 7.7 % | 149 | 74.9 % | 5165 | 3897 / 5165 = 75.5 % | [74.3–76.6] | 917 = 17.8 % | 351 = 6.8 % | 152 |

Differanse 3 mot 0 flagg: +40.9 pp [+36.5; +45.0] (730 d); +38.1 pp [+34.3; +41.6] (as-of). Univariat AUC for antall flagg (730 d): 0.701; χ²-test p = 6.7e-92.

### 1.4 Sensitivitet — flagg (3) bare «ikke levert» (for unge selskaper får ikke flagget)

Korrigert revisorflagg; flagg (3) uten «for ungt».

| Flagg | n (730 d) | Innstilt innen 730 d | Wilson 95 % | Ordinært avsluttet ≤730 d | Fortsatt åpent dag 730 | Median dager til innstilling (innstilte ≤730 d) | AJ 730 d (alle 5 165) | n (as-of) | Innstilt as-of 24.08.2026 | Wilson 95 % | Ord. avsl. as-of | Åpne as-of | Median dager (innstilte as-of) |
|---|---:|---|---|---|---|---:|---|---:|---|---|---|---|---:|
| 0 | 801 | 392 / 801 = 48.9 % | [45.5–52.4] | 237 = 29.6 % | 172 = 21.5 % | 263 | 49.2 % | 1079 | 550 / 1079 = 51.0 % | [48.0–53.9] | 355 = 32.9 % | 174 = 16.1 % | 268 |
| 1 | 845 | 593 / 845 = 70.2 % | [67.0–73.2] | 192 = 22.7 % | 60 = 7.1 % | 196 | 70.8 % | 1148 | 817 / 1148 = 71.2 % | [68.5–73.7] | 242 = 21.1 % | 89 = 7.8 % | 201 |
| 2 | 1841 | 1561 / 1841 = 84.8 % | [83.1–86.4] | 227 = 12.3 % | 53 = 2.9 % | 125 | 85.2 % | 2529 | 2160 / 2529 = 85.4 % | [84.0–86.7] | 294 = 11.6 % | 75 = 3.0 % | 126 |
| 3 | 285 | 266 / 285 = 93.3 % | [89.8–95.7] | 14 = 4.9 % | 5 = 1.8 % | 109 | 90.4 % | 409 | 370 / 409 = 90.5 % | [87.2–92.9] | 26 = 6.4 % | 13 = 3.2 % | 114 |
| **Alle** | 3772 | 2812 / 3772 = 74.5 % | [73.1–75.9] | 670 = 17.8 % | 290 = 7.7 % | 149 | 74.9 % | 5165 | 3897 / 5165 = 75.5 % | [74.3–76.6] | 917 = 17.8 % | 351 = 6.8 % | 152 |

Differanse 3 mot 0 flagg: +44.4 pp [+39.5; +48.6] (730 d); +39.5 pp [+35.1; +43.4] (as-of). Univariat AUC for antall flagg (730 d): 0.704; χ²-test p = 4.4e-95.

### 1.5 De åtte flaggkombinasjonene (korrigert flagg)

| Balanse < 1 mill./ingen | Ingen revisor ved åpningen | Siste pliktige regnskap ikke levert/for ungt | Flagg | n (730 d) | Innstilt innen 730 d | Wilson 95 % | n (as-of) | Innstilt as-of |
|---|---|---|---:|---:|---|---|---:|---|
| nei | nei | nei | 0 | 792 | 387 / 792 = 48.9 % | [45.4–52.3] | 1068 | 544 / 1068 = 50.9 % |
| nei | nei | ja | 1 | 84 | 55 / 84 = 65.5 % | [54.8–74.8] | 145 | 88 / 145 = 60.7 % |
| nei | ja | nei | 1 | 629 | 447 / 629 = 71.1 % | [67.4–74.5] | 830 | 604 / 830 = 72.8 % |
| nei | ja | ja | 2 | 84 | 59 / 84 = 70.2 % | [59.8–79.0] | 139 | 104 / 139 = 74.8 % |
| ja | nei | nei | 1 | 97 | 70 / 97 = 72.2 % | [62.5–80.1] | 128 | 97 / 128 = 75.8 % |
| ja | nei | ja | 2 | 35 | 23 / 35 = 65.7 % | [49.2–79.2] | 41 | 27 / 41 = 65.9 % |
| ja | ja | nei | 2 | 1442 | 1225 / 1442 = 85.0 % | [83.0–86.7] | 1988 | 1697 / 1988 = 85.4 % |
| ja | ja | ja | 3 | 609 | 546 / 609 = 89.7 % | [87.0–91.8] | 826 | 736 / 826 = 89.1 % |

### 1.6 Kryss: sum eiendeler × revisor registrert ved åpningen (730 d; as-of i parentes)

| Sum eiendeler | Ingen revisor ved åpningen | Revisor registrert ved åpningen |
|---|---|---|
| Ingen regnskap | 213 / 239 = 89.1 % [84.5–92.5] (as-of 285 / 317 = 89.9 %) | 8 / 15 = 53.3 % [30.1–75.2] (as-of 8 / 17 = 47.1 %) |
| <1 mill. | 1558 / 1812 = 86.0 % [84.3–87.5] (as-of 2148 / 2497 = 86.0 %) | 85 / 117 = 72.6 % [63.9–79.9] (as-of 116 / 152 = 76.3 %) |
| 1–<5 mill. | 427 / 597 = 71.5 % [67.8–75.0] (as-of 593 / 812 = 73.0 %) | 241 / 409 = 58.9 % [54.1–63.6] (as-of 324 / 566 = 57.2 %) |
| ≥5 mill. | 79 / 116 = 68.1 % [59.2–75.9] (as-of 115 / 157 = 73.2 %) | 201 / 467 = 43.0 % [38.6–47.6] (as-of 308 / 647 = 47.6 %) |

### 1.7 Kryss: revisor registrert ved åpningen × siste pliktige regnskap (730 d)

| Revisor ved åpningen | Levert | Ikke levert | For ungt |
|---|---|---|---|
| nei | 1672 / 2071 = 80.7 % [79.0–82.4] | 304 / 338 = 89.9 % [86.3–92.7] | 301 / 355 = 84.8 % [80.7–88.2] |
| ja | 457 / 889 = 51.4 % [48.1–54.7] | 68 / 97 = 70.1 % [60.4–78.3] | 10 / 22 = 45.5 % [26.9–65.3] |

## 2. Ut-av-utvalg-kontroll (50/50-splitt)

### 2.1 Samme splitt som V-B2 (seed 2026), terskler faste (1 mill.; revisor ved åpningen; levert)

| Flagg | Treningshalvdel | Testhalvdel | Wilson 95 % (test) |
|---|---|---|---|
| 0 | 202 / 396 = 51.0 % | 185 / 396 = 46.7 % | [41.9–51.6] |
| 1 | 276 / 401 = 68.8 % | 296 / 409 = 72.4 % | [67.8–76.5] |
| 2 | 641 / 780 = 82.2 % | 666 / 781 = 85.3 % | [82.6–87.6] |
| 3 | 274 / 309 = 88.7 % | 272 / 300 = 90.7 % | [86.8–93.5] |

AUC for antall flagg: hele fullvinduet 0.701; treningshalvdel 0.684; testhalvdel 0.718. (V-B2 med gammelt flagg: 0,693 i utvalget, 0,707 på testhalvdelen.)

Samme splitt med B2s gamle flagg (skal gi V-B2s 51,8 / 75,7 / 85,3 / 91,2 på testhalvdelen): 51.8 / 75.7 / 85.3 / 91.2; AUC test 0.707.

### 2.2 Terskelen for balansen valgt på treningshalvdelen (kandidater 0,1 / 0,25 / 0,5 / 1 / 2 / 5 mill.), deretter låst og anvendt på testhalvdelen

| Terskel | AUC trening | AUC test | Test: 0 / 1 / 2 / 3 flagg |
|---|---:|---:|---|
| 0.1 mill. | 0.667 | 0.717 | 48.6 / 78.4 / 90.6 / 93.0 |
| 0.25 mill. | 0.681 | 0.728 | 47.9 / 76.6 / 89.8 / 93.2 |
| 0.5 mill. | 0.690 | 0.728 | 47.3 / 75.3 / 87.1 / 92.6 |
| 1 mill. | 0.684 | 0.718 | 46.7 / 72.4 / 85.3 / 90.7 |
| 2 mill. | 0.677 | 0.717 | 43.8 / 66.6 / 84.0 / 90.2 |
| 5 mill. | 0.659 | 0.701 | 39.7 / 60.8 / 82.5 / 89.1 |

Valgt på treningshalvdelen: 0.5 mill. (AUC trening 0.690); på testhalvdelen gir den AUC 0.728.

### 2.3 500 tilfeldige 50/50-splitter (terskler faste): fordelingen av testhalvdelens andeler

| Størrelse | Snitt over 500 testhalvdeler | 2,5–97,5-persentil |
|---|---:|---|
| 0 flagg | 48.9 % | 45.6–52.4 % |
| 1 flagg | 70.6 % | 67.6–73.8 % |
| 2 flagg | 83.7 % | 81.8–85.5 % |
| 3 flagg | 89.6 % | 87.3–92.0 % |
| AUC antall flagg | 0.700 | 0.682–0.718 |

Terskel valgt på treningshalvdelen (500 splitter): 0.5 mill. 455 ganger, 0.25 mill. 33 ganger, 1 mill. 10 ganger, 2 mill. 2 ganger.

## 3. Den kompakte tre-signal-modellen (modell D) med korrigert flagg

**3.0 Reproduksjon: modell D med B2s gamle flagg (skal gi AUC 0,710, CV 0,703, OR revisor 0,56)** — n = 3772, hendelser = 2812, log-likelihood -1924.9 (konstant -2139.6), AUC in-sample = 0.710, 10-fold CV AUC = 0.703 (seed 1) / 0.699 (seed 7) / 0.699 (seed 42); snitt over 20 seeds 0.699.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| ta_m: <1 mill. (ref. 1–<5 mill.) | 2.359 | 1.945–2.862 | 2.9e-18 | 1929 |
| ta_m: Ingen regnskap | 2.707 | 1.688–4.343 | 3.61e-05 | 254 |
| ta_m: ≥5 mill. | 0.549 | 0.443–0.681 | 5.01e-08 | 583 |
| rev_ever: ja (mot nei) | 0.563 | 0.470–0.675 | 4.89e-10 | 1466 |
| lev_m: For ungt (ref. Levert) | 0.855 | 0.604–1.210 | 0.377 | 377 |
| lev_m: Ikke levert | 1.790 | 1.334–2.402 | 0.000104 | 435 |

**3.1 Modell D med revisor registrert ved åpningen** — n = 3772, hendelser = 2812, log-likelihood -1914.6 (konstant -2139.6), AUC in-sample = 0.714, 10-fold CV AUC = 0.706 (seed 1) / 0.704 (seed 7) / 0.701 (seed 42); snitt over 20 seeds 0.702.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| ta_m: <1 mill. (ref. 1–<5 mill.) | 2.164 | 1.775–2.640 | 2.49e-14 | 1929 |
| ta_m: Ingen regnskap | 2.583 | 1.609–4.149 | 8.6e-05 | 254 |
| ta_m: ≥5 mill. | 0.624 | 0.500–0.780 | 3.45e-05 | 583 |
| rev_open: ja (mot nei) | 0.457 | 0.375–0.558 | 1.08e-14 | 1008 |
| lev_m: For ungt (ref. Levert) | 0.906 | 0.641–1.279 | 0.573 | 377 |
| lev_m: Ikke levert | 1.886 | 1.404–2.533 | 2.47e-05 | 435 |

### 3.2 Predikerte sannsynligheter for typiske profiler (innstilt innen 730 d), korrigert flagg; B2s gamle tall i siste kolonne

| Profil | Predikert (modell D, korrigert) | 95 % KI | Observert i cellen (730 d) | Observert as-of (alle 5 165) | B2/V-B2 (gammelt flagg): predikert / observert |
|---|---:|---|---|---|---|
| Eiendeler ≥ 5 mill., revisor registrert ved åpningen, regnskap levert | 43.1 % | 39.0–47.3 | 175 / 427 = 41.0 % [36.4–45.7] | 265 / 574 = 46.2 % | 45.0 % / 202 / 460 = 43.9 % |
| Eiendeler 1–5 mill., revisor registrert, regnskap levert | 54.8 % | 50.5–59.1 | 212 / 365 = 58.1 % [53.0–63.0] | 279 / 494 = 56.5 % | 59.9 % / 311 / 506 = 61.5 % |
| Eiendeler 1–5 mill., ingen revisor, regnskap levert | 72.6 % | 69.3–75.8 | 374 / 521 = 71.8 % [67.8–75.5] | 505 / 692 = 73.0 % | 72.6 % / 275 / 380 = 72.4 % |
| Eiendeler < 1 mill., ingen revisor, regnskap levert | 85.2 % | 83.4–86.8 | 1213 / 1428 = 84.9 % [83.0–86.7] | 1675 / 1963 = 85.3 % | 86.2 % / 1014 / 1183 = 85.7 % |
| Eiendeler < 1 mill., ingen revisor, siste regnskap ikke levert | 91.6 % | 89.0–93.6 | 214 / 230 = 93.0 % [89.0–95.7] | 300 / 330 = 90.9 % | 91.8 % / 197 / 211 = 93.4 % |
| Ingen balanse, ingen revisor, siste regnskap ikke levert | 92.8 % | 88.6–95.5 | 52 / 55 = 94.5 % [85.1–98.1] | 70 / 79 = 88.6 % | 92.8 % / 51 / 54 = 94.4 % |
| Ingen balanse, ingen revisor, for ungt | 86.1 % | 81.0–90.1 | 149 / 170 = 87.6 % [81.9–91.8] | 193 / 213 = 90.6 % | 86.0 % / 149 / 169 = 88.2 % |

## 4. Revisorkontrasten: univariat og justert

### 4.1 Univariat (tre tilstander ved dag 730 og as-of)

| Revisor ved åpningen | n (730 d) | Innstilt innen 730 d | Wilson 95 % | Ord. avsl. ≤730 d | Åpent dag 730 | Median dager | AJ 730 d | n (as-of) | Innstilt as-of | Wilson 95 % | Ord. avsl. as-of | Åpne as-of |
|---|---:|---|---|---|---|---:|---|---:|---|---|---|---|
| registrert (siste Revisor-felt = navn) | 1008 | 535 / 1008 = 53.1 % | [50.0–56.1] | 28.2 % | 18.8 % | 243 | 53.3 % | 1382 | 756 / 1382 = 54.7 % | [52.1–57.3] | 30.0 % | 15.3 % |
| ikke registrert (aldri kunngjort, eller «Utgår») | 2764 | 2277 / 2764 = 82.4 % | [80.9–83.8] | 14.0 % | 3.7 % | 134 | 82.8 % | 3783 | 3141 / 3783 = 83.0 % | [81.8–84.2] | 13.3 % | 3.7 % |
| — derav aldri kunngjort revisor | 2306 | 1921 / 2306 = 83.3 % | [81.7–84.8] | 13.2 % | 3.5 % | 133 | 83.7 % | 3151 | 2648 / 3151 = 84.0 % | [82.7–85.3] | 12.6 % | 3.3 % |
| — derav siste verdi «Utgår» (strøket) | 458 | 356 / 458 = 77.7 % | [73.7–81.3] | 17.7 % | 4.6 % | 142 | 78.1 % | 632 | 493 / 632 = 78.0 % | [74.6–81.1] | 16.6 % | 5.4 % |

Differanse uten − med revisor: +29.3 pp [+25.9; +32.7] (730 d); +28.3 pp [+25.4; +31.2] (as-of). B2s gamle flagg: +22.5 pp [+19.6; +25.4] (730 d).

### 4.2 Modell A, V-B2s spesifikasjon (12 blokker) — justert OR for revisor

**4.2a Gammelt flagg (skal gi V-B2s 0,665 [0,521–0,848], AUC 0,749)** — n = 3772, hendelser = 2812, log-likelihood -1853.8 (konstant -2139.6), AUC in-sample = 0.748, 10-fold CV AUC = 0.740 (seed 1) / 0.737 (seed 7) / 0.738 (seed 42); snitt over 20 seeds 0.738.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| oppbud: ja (mot nei) | 0.955 | 0.786–1.160 | 0.644 | 2745 |
| ta_m: <1 mill. (ref. 1–<5 mill.) | 1.569 | 1.256–1.959 | 7.31e-05 | 1929 |
| ta_m: Ingen regnskap | 3.292 | 1.991–5.445 | 3.44e-06 | 254 |
| ta_m: ≥5 mill. | 0.617 | 0.474–0.802 | 0.000305 | 583 |
| lev_m: For ungt (ref. Levert) | 0.994 | 0.600–1.646 | 0.982 | 377 |
| lev_m: Ikke levert | 1.779 | 1.298–2.439 | 0.000346 | 435 |
| REV: ja (mot nei) | 0.667 | 0.523–0.851 | 0.00111 | 1466 |
| dl_utgaar_12m: ja (mot nei) | 2.384 | 1.236–4.599 | 0.00954 | 79 |

**4.2b Korrigert flagg (V-B2 fant 0,655 [0,507–0,847])** — n = 3772, hendelser = 2812, log-likelihood -1854.0 (konstant -2139.6), AUC in-sample = 0.748, 10-fold CV AUC = 0.740 (seed 1) / 0.737 (seed 7) / 0.738 (seed 42); snitt over 20 seeds 0.738.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| oppbud: ja (mot nei) | 0.960 | 0.790–1.167 | 0.682 | 2745 |
| ta_m: <1 mill. (ref. 1–<5 mill.) | 1.581 | 1.266–1.975 | 5.43e-05 | 1929 |
| ta_m: Ingen regnskap | 3.317 | 2.006–5.484 | 2.96e-06 | 254 |
| ta_m: ≥5 mill. | 0.647 | 0.495–0.846 | 0.00143 | 583 |
| lev_m: For ungt (ref. Levert) | 0.991 | 0.599–1.641 | 0.973 | 377 |
| lev_m: Ikke levert | 1.811 | 1.321–2.483 | 0.000225 | 435 |
| REV: ja (mot nei) | 0.657 | 0.509–0.849 | 0.0013 | 1008 |
| dl_utgaar_12m: ja (mot nei) | 2.396 | 1.242–4.622 | 0.00916 | 79 |

**4.2c Begge revisorvariabler i samme modell (V-B2s spesifikasjon)** — n = 3772, hendelser = 2812, log-likelihood -1852.6 (konstant -2139.6), AUC in-sample = 0.749, 10-fold CV AUC = 0.740 (seed 1) / 0.737 (seed 7) / 0.738 (seed 42); snitt over 20 seeds 0.738.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| REV: ja (mot nei) | 0.776 | 0.563–1.069 | 0.12 | 1008 |
| REV2: ja (mot nei) | 0.771 | 0.568–1.047 | 0.0962 | 1466 |

### 4.3 Modell A, B2s fulle spesifikasjon (19 blokker, 41 koeffisienter) — justert OR for revisor

**4.3a Gammelt flagg (skal gi B2s 0,65 [0,51–0,84], AUC 0,750, CV 0,735)** — n = 3772, hendelser = 2812, log-likelihood -1847.6 (konstant -2139.6), AUC in-sample = 0.750, 10-fold CV AUC = 0.735 (seed 1) / 0.732 (seed 7) / 0.734 (seed 42); snitt over 20 seeds 0.733.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| oppbud: ja (mot nei) | 0.944 | 0.774–1.153 | 0.574 | 2745 |
| bransje_m: C Industri (ref. Øvrige/uklassifisert) | 0.931 | 0.600–1.446 | 0.751 | 154 |
| bransje_m: F Bygg og anlegg, utførende (41.2, 42, 43) | 0.998 | 0.748–1.330 | 0.988 | 934 |
| bransje_m: G Varehandel og bilverksted | 1.158 | 0.861–1.557 | 0.332 | 742 |
| bransje_m: H Transport og lagring | 1.154 | 0.742–1.793 | 0.525 | 179 |
| bransje_m: I Overnatting og servering | 1.280 | 0.904–1.812 | 0.164 | 420 |
| bransje_m: L Fast eiendom (utleie, forvaltning, kjøp/salg) | 0.996 | 0.677–1.464 | 0.982 | 259 |
| bransje_m: M Faglig, vitenskapelig og teknisk tjenesteyting | 1.129 | 0.771–1.653 | 0.534 | 299 |
| bransje_m: N Forretningsmessig tjenesteyting (bemanning, renhold, utleie) | 1.095 | 0.718–1.670 | 0.672 | 202 |
| bransje_m: Uoppgitt | 5.873 | 1.768–19.509 | 0.00385 | 84 |
| ta_m: <1 mill. (ref. 1–<5 mill.) | 1.543 | 1.232–1.934 | 0.000164 | 1929 |
| ta_m: Ingen regnskap før åpning | 3.394 | 2.046–5.630 | 2.21e-06 | 254 |
| ta_m: ≥5 mill. | 0.657 | 0.501–0.861 | 0.00232 | 583 |
| levert_m: Ikke aktuelt (ungt) (ref. Ja) | 1.004 | 0.605–1.666 | 0.988 | 377 |
| levert_m: Nei | 1.805 | 1.314–2.479 | 0.000263 | 435 |
| dl_utgaar_12m: ja (mot nei) | 2.498 | 1.283–4.864 | 0.00708 | 79 |
| REV: ja (mot nei) | 0.654 | 0.509–0.838 | 0.000818 | 1466 |
| revisor_utgaar_12m: ja (mot nei) | 1.185 | 0.726–1.933 | 0.498 | 101 |

**4.3b Korrigert flagg** — n = 3772, hendelser = 2812, log-likelihood -1847.8 (konstant -2139.6), AUC in-sample = 0.749, 10-fold CV AUC = 0.735 (seed 1) / 0.731 (seed 7) / 0.734 (seed 42); snitt over 20 seeds 0.733.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| oppbud: ja (mot nei) | 0.954 | 0.781–1.166 | 0.647 | 2745 |
| bransje_m: C Industri (ref. Øvrige/uklassifisert) | 0.934 | 0.601–1.451 | 0.762 | 154 |
| bransje_m: F Bygg og anlegg, utførende (41.2, 42, 43) | 1.000 | 0.750–1.333 | 1 | 934 |
| bransje_m: G Varehandel og bilverksted | 1.150 | 0.855–1.546 | 0.356 | 742 |
| bransje_m: H Transport og lagring | 1.145 | 0.737–1.778 | 0.547 | 179 |
| bransje_m: I Overnatting og servering | 1.277 | 0.902–1.807 | 0.168 | 420 |
| bransje_m: L Fast eiendom (utleie, forvaltning, kjøp/salg) | 0.975 | 0.663–1.433 | 0.896 | 259 |
| bransje_m: M Faglig, vitenskapelig og teknisk tjenesteyting | 1.150 | 0.785–1.685 | 0.474 | 299 |
| bransje_m: N Forretningsmessig tjenesteyting (bemanning, renhold, utleie) | 1.089 | 0.714–1.659 | 0.693 | 202 |
| bransje_m: Uoppgitt | 5.591 | 1.681–18.600 | 0.00501 | 84 |
| ta_m: <1 mill. (ref. 1–<5 mill.) | 1.551 | 1.238–1.944 | 0.000138 | 1929 |
| ta_m: Ingen regnskap før åpning | 3.429 | 2.068–5.685 | 1.78e-06 | 254 |
| ta_m: ≥5 mill. | 0.686 | 0.521–0.903 | 0.00725 | 583 |
| levert_m: Ikke aktuelt (ungt) (ref. Ja) | 1.004 | 0.605–1.664 | 0.989 | 377 |
| levert_m: Nei | 1.823 | 1.328–2.502 | 0.000205 | 435 |
| dl_utgaar_12m: ja (mot nei) | 2.514 | 1.293–4.891 | 0.00661 | 79 |
| REV: ja (mot nei) | 0.643 | 0.494–0.836 | 0.00101 | 1008 |
| revisor_utgaar_12m: ja (mot nei) | 0.823 | 0.503–1.347 | 0.439 | 101 |

### 4.4 Modell helt uten regnskapstall (V-B2s T5: oppbud, næring, alder, aksjekapital, varsel, revisor, regnskap levert, åpningsår)

**4.4a Gammelt flagg (V-B2: AUC 0,690, CV 0,673)** — n = 3772, hendelser = 2812, log-likelihood -1983.8 (konstant -2139.6), AUC in-sample = 0.679, 10-fold CV AUC = 0.668 (seed 1) / 0.665 (seed 7) / 0.668 (seed 42); snitt over 20 seeds 0.667.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| REV: ja (mot nei) | 0.325 | 0.265–0.399 | 2.86e-27 | 1466 |

**4.4b Korrigert flagg** — n = 3772, hendelser = 2812, log-likelihood -1947.5 (konstant -2139.6), AUC in-sample = 0.695, 10-fold CV AUC = 0.683 (seed 1) / 0.680 (seed 7) / 0.682 (seed 42); snitt over 20 seeds 0.682.

| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |
|---|---:|---|---:|---:|
| REV: ja (mot nei) | 0.275 | 0.228–0.330 | 1.12e-42 | 1008 |

