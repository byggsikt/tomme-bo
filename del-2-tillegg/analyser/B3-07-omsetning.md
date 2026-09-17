# B3-07 driftsinntekter (as-of 24.08.2026 / fasthorisont 730 d)

## Stratifisert paa driftsinntektsbaand (siste regnskap foer aapningsaaret)

| Baand | Bygg n / andel | Oevrige n / andel | Bygg innstilt as-of | Oevrige as-of | Bygg innen 730 d | Oevrige innen 730 d | Diff 730 d [Newcombe] | Bygg CIF730 | Oevrige CIF730 |
|---|---|---|---|---|---|---|---|---|---|
| 0 ingen regnskap | 104 (8.1 %) | 228 (5.9 %) | 88/104 = 84.6 % | 205/228 = 89.9 % | 68/81 = 84.0 % | 153/172 = 89.0 % | -5.0 pp [-15.3; +3.5] | 83.9 % | 89.4 % |
| 1 mangler | 45 (3.5 %) | 430 (11.1 %) | 39/45 = 86.7 % | 376/430 = 87.4 % | 27/30 = 90.0 % | 274/316 = 86.7 % | +3.3 pp [-12.7; +11.1] | 91.1 % | 87.5 % |
| 2 <1 MNOK | 211 (16.5 %) | 1075 (27.7 %) | 186/211 = 88.2 % | 950/1075 = 88.4 % | 128/147 = 87.1 % | 694/790 = 87.8 % | -0.8 pp [-7.5; +4.4] | 88.5 % | 87.9 % |
| 3 1-5 MNOK | 452 (35.3 %) | 1221 (31.4 %) | 361/452 = 79.9 % | 939/1221 = 76.9 % | 255/324 = 78.7 % | 683/902 = 75.7 % | +3.0 pp [-2.5; +8.0] | 80.0 % | 76.6 % |
| 4 5-20 MNOK | 323 (25.2 %) | 689 (17.7 %) | 186/323 = 57.6 % | 409/689 = 59.4 % | 141/245 = 57.6 % | 289/485 = 59.6 % | -2.0 pp [-9.6; +5.4] | 56.2 % | 58.6 % |
| 5 >=20 MNOK | 145 (11.3 %) | 242 (6.2 %) | 51/145 = 35.2 % | 107/242 = 44.2 % | 35/107 = 32.7 % | 65/173 = 37.6 % | -4.9 pp [-15.9; +6.7] | 32.6 % | 41.3 % |

Raa 730-d differanse -6.0 pp; bygg standardisert til oevriges driftsinntektsfordeling 76.2 % mot oevrige 76.0 % -> +0.2 pp; Mantel-Haenszel OR 0.982.

## Modeller (730 d, n = 3772)

| Modell | par. | OR bygg [95 %] | p | Marginal RD [95 %] |
|---|---|---|---|---|
| M0 bygg | 2 | 0.736 [0.624; 0.868] | 0.00026 | -6.0 pp [-9.8; -2.7] |
| bygg + log10(driftsinntekter) + kvadrat + mangler-flagg + ingen-regnskap | 6 | 0.984 [0.822; 1.178] | 0.86 | -0.3 pp [-3.3; +2.6] |
| M7 full (stoerrelse, oppbud, avstand, alder, rettskrets, driftsinntektsbaand) | 39 | 0.865 [0.715; 1.047] | 0.14 | -2.3 pp [-5.8; +0.9] |
| M7 + bygg x driftsinntektsbaand | 43 | 0.683 [0.438; 1.065] | 0.093 | -2.6 pp [-5.7; +0.8] |
| M7 + bygg x oppbud | 39 | 0.865 [0.715; 1.047] | 0.14 | -2.3 pp [-5.1; +0.9] |

LR-test M7 + bygg x driftsinntektsbaand: chi2 = 2.54, df = 4, p = 0.637; ledd: revband=1 mangler: x1.16 (se 0.68); revband=3 1-5 MNOK: x1.52 (se 0.28); revband=4 5-20 MNOK: x1.23 (se 0.28); revband=5 >=20 MNOK: x1.16 (se 0.35)

LR-test M7 + bygg x oppbud: chi2 = 0.00, df = 0, p = nan; ledd: 

M7 + bygg x oppbud (manuelt ledd): LR chi2 = 4.20, df 1, p = 0.041; OR bygg blant begjaering 1.153 [0.823; 1.615]; multiplikator for oppbud x0.66 (se 0.20) -> OR bygg blant oppbud 0.760.

M7 med omraade F (41-43) som byggmerke: OR 0.926 [0.771; 1.112], RD -1.2 pp [-4.2; +1.3].

M7 paa as-of-utfallet, alle 5 165: OR 0.885 [0.752; 1.041], RD -2.0 pp [-4.7; +0.7].

Spearman(driftsinntekter, sum eiendeler) blant 4358 med begge: 0.70. Bygg: median driftsinntekter/sum eiendeler 3.47; oevrige 2.48.

Driftsinntekter mangler (NULL) blant dem med regnskap: bygg 45/1176, oevrige 430/3657; driftsinntekter = 0 (rapportert null): bygg 22, oevrige 177.

