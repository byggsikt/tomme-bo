## (a) Utfall per 24.08.2026 etter åpningsgrunnlag (as-of, hele kohorten)

| Grunnlag | n | innstilt § 135 | % [Wilson 95 %] | ordinær avslutning | % [95 %] | fortsatt åpne | % [95 %] |
|---|---:|---:|---:|---:|---:|---:|---:|
| Oppbud (felt «Åpnet etter: Oppbud») | 3734 | 2772 | 74.2 [72.8–75.6] | 714 | 19.1 [17.9–20.4] | 248 | 6.6 [5.9–7.5] |
| Ikke registrert som oppbud (= begjæring fra andre) | 1431 | 1125 | 78.6 [76.4–80.7] | 203 | 14.2 [12.5–16.1] | 103 | 7.2 [6.0–8.7] |
| **Differanse begjæring − oppbud** | | | **+4.4 pp** [Newcombe +1.8; +6.9] | | | | |

χ²(Yates) = 10.48, p = 1.21e-03. Dekning: grunnlaget er definert for 5 165/5 165 (100,0 %).

## (b) Antakelsesfri 24-månedersandel — delkohort åpnet ≤ 24.08.2024 (full 730-dagers oppfølging)

| Grunnlag | n (åpnet ≤ 2024-08-24) | innstilt innen 730 d | % [Wilson 95 %] | [Clopper–Pearson] | avsluttet innen 730 d (uten innstilling) | % | verken innen 730 d | % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Oppbud (felt «Åpnet etter: Oppbud») | 2745 | 2000 | 72.9 [71.2–74.5] | [71.2–74.5] | 528 | 19.2 | 217 | 7.9 |
| Ikke registrert som oppbud (= begjæring fra andre) | 1027 | 812 | 79.1 [76.5–81.4] | [76.4–81.5] | 142 | 13.8 | 73 | 7.1 |
| **Differanse begjæring − oppbud** | 3772 | | **+6.2 pp** [Newcombe +3.1; +9.1] | | | | | |

χ²(Yates) = 14.84, p = 1.17e-04. Ingen sensurering innenfor vinduet; ren binomisk andel, ingen konkurrerende-risiko-estimator.

## (c) Kumulativ insidens av innstilling (Aalen–Johansen, ordinær avslutning som konkurrerende hendelse)

Daglig tidsrutenett (hele dager fra åpningsdato). Risikomengde ved dag t = bo med observert tid ≥ t (verken innstilt, avsluttet eller sensurert før t). Sensurering 24.08.2026. Intervaller: deltametode-varians med log(−log)-transformasjon (Greenwood-type, samme formel som studiens rev2-00-lib) OG perkentil-bootstrap (2000 omtrekk av bo innen gruppen, frø 20260912).

| Grunnlag | horisont | CIF innstilling % | [delta log(−log) 95 %] | [bootstrap 95 %] | CIF ordinær avslutning % | fortsatt uavgjort % | risikomengde | hendelser innen horisont |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Oppbud (felt «Åpnet etter: Oppbud») | 12 mnd (365 d) | **62.96** | [61.39–64.49] | [61.30–64.54] | 9.13 | 27.91 | 1047 | 2351 |
| Oppbud (felt «Åpnet etter: Oppbud») | 18 mnd (548 d) | **70.92** | [69.43–72.34] | [69.36–72.36] | 14.22 | 14.86 | 555 | 2648 |
| Oppbud (felt «Åpnet etter: Oppbud») | 24 mnd (730 d) | **73.50** | [72.05–74.90] | [71.98–74.92] | 18.35 | 8.15 | 217 | 2737 |
| Ikke registrert som oppbud (= begjæring fra andre) | 12 mnd (365 d) | **63.80** | [61.25–66.23] | [61.35–66.32] | 6.22 | 29.98 | 430 | 913 |
| Ikke registrert som oppbud (= begjæring fra andre) | 18 mnd (548 d) | **74.63** | [72.30–76.81] | [72.47–76.87] | 10.69 | 14.68 | 210 | 1068 |
| Ikke registrert som oppbud (= begjæring fra andre) | 24 mnd (730 d) | **78.52** | [76.26–80.59] | [76.41–80.67] | 13.64 | 7.84 | 73 | 1116 |

### Kontrast begjæring − oppbud (risikodifferanse i CIF, prosentpoeng)

| horisont | CIF begjæring % | CIF oppbud % | RD pp | [Wald, delta 95 %] | [bootstrap 95 %] | z | p | RR | [RR 95 %] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 mnd | 63.80 | 62.96 | **+0.84** | [-2.09; +3.77] | [-2.00; +3.73] | 0.56 | 5.7e-01 | 1.013 | [0.968; 1.061] |
| 18 mnd | 74.63 | 70.92 | **+3.72** | [+1.03; +6.40] | [+1.10; +6.40] | 2.71 | 6.6e-03 | 1.052 | [1.015; 1.092] |
| 24 mnd | 78.52 | 73.50 | **+5.01** | [+2.42; +7.61] | [+2.54; +7.57] | 3.79 | 1.5e-04 | 1.068 | [1.033; 1.105] |

**Grays test** (Gray 1988, ρ = 0, subdistribusjonsrisikomengde, H0: CIF_begjæring(t) = CIF_oppbud(t) for alle t): U = 13.507, V = 790.369, z = 0.480, χ²(1) = 0.231, p = 6.31e-01.

## (d) Tid til innstilling

To ulike størrelser — de skal aldri blandes:

| Grunnlag | **CIF-basert dager til 50 % innstilt** (Aalen–Johansen-kvantil, sensureringsriktig, konkurrerende hendelse tatt hensyn til) | [testinversjon 95 %] | [bootstrap 95 %] | dager til 60 % | **Rå median blant fullførte innstillinger** (kun bo som ER innstilt; sensureringsbiasert, underdriver) | [bootstrap 95 %] | Q1 / Q3 | n innstilt |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Oppbud (felt «Åpnet etter: Oppbud») | **212** | [203–222] | [203–223] | 320 | **141.0** | [136.0–147.0] | 83 / 258 | 2772 |
| Ikke registrert som oppbud (= begjæring fra andre) | **238** | [225–255] | [225–253] | 319 | **182.0** | [171.0–195.0] | 104 / 311 | 1125 |
| **Differanse begjæring − oppbud** | **+26 dager** | | [+9; +44] | | +41.0 dager | | | |

## (e) Samme splitt innen utførende bygg og anlegg mot øvrige næringer

Byggmerket er reprodusert med studiens klassifikator (åpningsradens trykte etikett → SN2007 via `bransjekart-v3_2026-08-30.json`; utførende = 41.2, 42, 43): **1280 bo** (studien: 1 280), utfall 911/258/111 (studien: 911/258/111). Øvrige = komplementet, 3885 bo (inkl. uoppgitt).

Oppbudsandel: bygg **738/1280 = 57.7 %** [54.9–60.3] mot øvrige **2996/3885 = 77.1 %** [75.8–78.4]; differanse -19.5 pp [Newcombe -22.5; -16.5].

### Fire celler: grunnlag × næring

| Næring | Grunnlag | n | innstilt as-of | % [Wilson] | n full 730 d | innstilt ≤ 730 d | % [Wilson] | CIF 12 mnd % | CIF 18 mnd % | **CIF 24 mnd %** | [delta 95 %] | [bootstrap 95 %] | CIF-dager til 50 % | rå median (fullførte) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bygg | oppbud | 738 | 479 | 64.9 [61.4–68.3] | 550 | 347 | 63.1 [59.0–67.0] | 52.3 | 60.6 | **63.90** | [60.30–67.26] | [60.54–67.27] | 321 | 162 |
| bygg | begjaering | 542 | 432 | 79.7 [76.1–82.9] | 384 | 307 | 79.9 [75.7–83.6] | 63.8 | 75.6 | **79.91** | [76.19–83.12] | [76.56–83.39] | 240 | 189 |
| ovrige | oppbud | 2996 | 2293 | 76.5 [75.0–78.0] | 2195 | 1653 | 75.3 [73.5–77.1] | 65.6 | 73.5 | **75.87** | [74.29–77.37] | [74.35–77.38] | 196 | 137 |
| ovrige | begjaering | 889 | 693 | 78.0 [75.1–80.6] | 643 | 505 | 78.5 [75.2–81.5] | 63.8 | 74.0 | **77.69** | [74.77–80.32] | [74.97–80.32] | 235 | 175 |

### Kontraster ved 24 måneder (CIF-risikodifferanse, pp) og Grays test

| Kontrast | innen | RD pp | [Wald delta 95 %] | [bootstrap 95 %] | z | p | Grays z | Grays p | as-of RD pp [Newcombe] | 730-d RD pp [Newcombe] |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bygg − øvrige | oppbud | **-11.97** | [-15.78; -8.16] | [-15.68; -8.31] | -6.16 | 7.2e-10 | -7.04 | 1.9e-12 | -11.6 [-15.4; -7.9] | -12.2 [-16.7; -7.9] |
| bygg − øvrige | begjæring | **+2.22** | [-2.21; +6.65] | [-2.14; +6.63] | 0.98 | 3.3e-01 | 0.13 | 9.0e-01 | +1.8 [-2.7; +6.0] | +1.4 [-3.8; +6.4] |
| begjæring − oppbud | bygg | **+16.02** | [+11.11; +20.93] | [+11.33; +20.61] | 6.40 | 1.6e-10 | 4.89 | 1.0e-06 | +14.8 [+9.9; +19.5] | +16.9 [+11.0; +22.4] |
| begjæring − oppbud | øvrige | **+1.83** | [-1.35; +5.00] | [-1.47; +4.97] | 1.13 | 2.6e-01 | -1.29 | 2.0e-01 | +1.4 [-1.8; +4.4] | +3.2 [-0.5; +6.8] |

Referanse (samme data, uten grunnlagssplitt): bygg 70.62 % mot øvrige 76.28 % ved 24 mnd, RD -5.66 pp [-8.52; -2.81] (studien I2b: −5,70 [−8,56; −2,83]).

### Interaksjon og standardisering

- **Forskjell i forskjeller** (byggfordel innen oppbud minus byggfordel innen begjæring, CIF 24 mnd): **-14.19 pp** [bootstrap -19.91; -8.55].
- **Sammensetningsjustert byggfordel**: gir vi bygg samme oppbudsandel som øvrige (77.1 %), blir byggs 24-mnd CIF 67.56 % mot øvrige 76.28 % — justert RD **-8.72 pp** (ujustert -5.66 pp). Andelen av byggfordelen som skyldes ulik oppbudsandel: -54 %.

### Logistisk regresjon (IRLS, egen implementasjon) — innstilt ~ begjæring + bygg (+ interaksjon) + rettskrets (22 dummyer, ref. Oslo)

| Modell | vindu | n | OR begjæring [95 %] | p | OR bygg [95 %] | p | OR interaksjon begjæring×bygg [95 %] | p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| uten interaksjon, krets-justert | as-of 24.08.2026 (alle 5 165; ulik oppfølging 601–1 088 d) | 5165 | 1.376 [1.180; 1.604] | 4.4e-05 | 0.702 [0.606; 0.813] | 2.4e-06 | — | — |
| med interaksjon, krets-justert | as-of 24.08.2026 (alle 5 165; ulik oppfølging 601–1 088 d) | 5165 | 1.098 [0.914; 1.319] | 3.2e-01 | 0.570 [0.479; 0.680] | 3.7e-10 | 1.932 [1.407; 2.651] | 0.00 |
| uten interaksjon, IKKE krets-justert | as-of 24.08.2026 (alle 5 165; ulik oppfølging 601–1 088 d) | 5165 | 1.366 [1.177; 1.586] | 4.2e-05 | 0.700 [0.605; 0.809] | 1.5e-06 | — | — |
| uten interaksjon, krets-justert | fast 730 d (delkohort åpnet ≤ 24.08.2024) | 3772 | 1.530 [1.277; 1.833] | 4.0e-06 | 0.677 [0.571; 0.803] | 7.8e-06 | — | — |
| med interaksjon, krets-justert | fast 730 d (delkohort åpnet ≤ 24.08.2024) | 3772 | 1.229 [0.990; 1.526] | 6.1e-02 | 0.560 [0.458; 0.685] | 1.8e-08 | 1.892 [1.302; 2.750] | 0.00 |
| uten interaksjon, IKKE krets-justert | fast 730 d (delkohort åpnet ≤ 24.08.2024) | 3772 | 1.510 [1.267; 1.801] | 4.4e-06 | 0.682 [0.577; 0.807] | 8.3e-06 | — | — |

## (f) Etter rettskrets — de 10 største tingrettene (åpningsradens tingrettsnavn; 23 kretser i kohortvinduet)

| Tingrett | n | oppbud n (%) | as-of innstilt oppbud % | as-of innstilt begjæring % | as-of RD pp [Newcombe] | 730-d innstilt oppbud (k/n) | 730-d begjæring (k/n) | CIF 24 mnd oppbud % [delta] | CIF 24 mnd begjæring % [delta] | **RD 24 mnd pp** [delta Wald] | [bootstrap] | Grays p | CIF-dager til 50 % oppbud / begjæring |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OSLO TINGRETT | 911 | 527 (57.8) | 74.8 (394/527) | 81.8 (314/384) | +7.0 [+1.6; +12.3] | 72.7 (296/407) | 79.5 (221/278) | 73.4 [69.4–76.9] | 81.1 [76.8–84.6] | **+7.7** [+2.2; +13.2] | [+2.0; +13.2] | 0.007 | 276 / 227 |
| TRØNDELAG TINGRETT | 413 | 351 (85.0) | 78.3 (275/351) | 87.1 (54/62) | +8.7 [-2.5; +16.5] | 72.3 (180/249) | 83.7 (36/43) | 77.2 [72.5–81.3] | 87.1 [75.9–93.3] | **+9.9** [+0.5; +19.3] | [+0.2; +19.1] | 0.451 | 153 / 175 |
| HORDALAND TINGRETT | 398 | 288 (72.4) | 64.9 (187/288) | 71.8 (79/110) | +6.9 [-3.6; +16.3] | 63.8 (139/218) | 73.8 (59/80) | 64.0 [58.1–69.3] | 72.1 [62.4–79.8] | **+8.1** [-2.2; +18.4] | [-2.2; +18.8] | 0.663 | 221 / 230 |
| ROMERIKE OG GLÅMDAL TINGRETT | 365 | 232 (63.6) | 74.1 (172/232) | 78.9 (105/133) | +4.8 [-4.5; +13.3] | 71.0 (120/169) | 76.9 (80/104) | 74.1 [68.0–79.3] | 78.9 [71.0–85.0] | **+4.8** [-4.1; +13.7] | [-3.7; +13.0] | 0.707 | 197 / 205 |
| AGDER TINGRETT | 321 | 260 (81.0) | 73.5 (191/260) | 72.1 (44/61) | -1.3 [-14.6; +9.9] | 72.6 (130/179) | 82.9 (34/41) | 73.6 [67.7–78.5] | 76.1 [61.9–85.6] | **+2.6** [-10.3; +15.5] | [-10.5; +15.7] | 0.141 | 257 / 412 |
| RINGERIKE, ASKER OG BÆRUM TINGRETT | 310 | 209 (67.4) | 71.8 (150/209) | 73.3 (74/101) | +1.5 [-9.5; +11.5] | 71.0 (110/155) | 71.6 (48/67) | 72.1 [65.4–77.7] | 73.0 [63.1–80.7] | **+1.0** [-9.8; +11.7] | [-10.5; +11.5] | 0.620 | 234 / 317 |
| VESTFOLD TINGRETT | 273 | 204 (74.7) | 72.1 (147/204) | 76.8 (53/69) | +4.8 [-7.8; +15.4] | 79.2 (122/154) | 87.2 (41/47) | 72.2 [65.4–78.0] | 80.7 [68.3–88.6] | **+8.4** [-3.3; +20.2] | [-3.3; +19.7] | 0.595 | 210 / 286 |
| SØR-ROGALAND TINGRETT | 267 | 214 (80.1) | 71.5 (153/214) | 71.7 (38/53) | +0.2 [-14.2; +12.4] | 69.6 (110/158) | 73.5 (25/34) | 70.1 [63.5–75.7] | 69.5 [54.3–80.4] | **-0.6** [-15.0; +13.8] | [-16.3; +13.6] | 0.169 | 232 / 388 |
| MØRE OG ROMSDAL TINGRETT | 245 | 201 (82.0) | 82.1 (165/201) | 81.8 (36/44) | -0.3 [-14.8; +10.2] | 79.9 (119/149) | 85.7 (30/35) | 80.2 [74.0–85.1] | 81.8 [66.9–90.5] | **+1.6** [-11.1; +14.3] | [-12.7; +13.7] | 0.565 | 161 / 128 |
| SØNDRE ØSTFOLD TINGRETT | 231 | 165 (71.4) | 69.1 (114/165) | 80.3 (53/66) | +11.2 [-1.7; +22.0] | 70.8 (80/113) | 80.4 (41/51) | 69.4 [61.7–75.8] | 80.6 [68.8–88.4] | **+11.3** [-0.7; +23.2] | [-0.7; +22.6] | 0.492 | 165 / 182 |

### Overlever begjæringseffekten innen rettskretsene? (alle 23 kretser som strata)

| Metode | vindu | estimat begjæring vs oppbud | 95 % | p |
|---|---|---:|---:|---:|
| Grays test stratifisert på rettskrets (ΣU/√ΣV, 23 strata) | AJ-kurver | z = 0.952 | | 3.41e-01 |
| Inverse-varians-poolet CIF-risikodifferanse ved 24 mnd (20 kretser med ≥ 10 bo i hver gruppe) | fast 730 d, AJ | +5.56 pp | [+2.92; +8.21] | Cochran Q = 14.9, df = 19, p_het = 0.73 |
| Mantel–Haenszel OR (RBG-varians) | as-of | 1.283 | [1.105; 1.489] | |
| Mantel–Haenszel OR (RBG-varians) | fast 730 d, delkohort | 1.424 | [1.193; 1.699] | |
| Cochran–MH-vektet risikodifferanse | as-of | +4.49 pp | [+1.89; +7.09] | |
| Cochran–MH-vektet risikodifferanse | fast 730 d, delkohort | +6.38 pp | [+3.34; +9.41] | |

Fortegn: begjæringsboene har høyere 24-mnd CIF enn oppbudsboene i **19 av 23** kretser (as-of-andel: 18 av 23).

### Byggfordelen innen rettskrets, per grunnlag (Grays test stratifisert på rettskrets)

| Delmengde | bygg n | øvrige n | Grays z (stratifisert på krets) | p | ustratifisert Grays z | p |
|---|---:|---:|---:|---:|---:|---:|
| innen oppbud | 738 | 2996 | -7.213 | 5.47e-13 | -7.041 | 1.91e-12 |
| innen begjæring | 542 | 889 | 0.376 | 7.07e-01 | 0.128 | 8.99e-01 |
| alle grunnlag | 1280 | 3885 | -5.687 | 1.29e-08 | -5.653 | 1.58e-08 |

