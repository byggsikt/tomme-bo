-- B2 supplement: postcode-based move flags (adresse.kommune is unusable: mixed number/name formats and multi-line reform values).
-- n_postnr_24m = distinct postcodes seen on the company's announced addresses (kilde 'ny' = new address in an address-change announcement,
-- 'gjeldende' = address printed on any announcement) in the 730 days before opening; n_postnr2_24m = distinct 2-digit postcode regions.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT o.orgnr,
       count(DISTINCT a.postnr) FILTER (WHERE a.dato >= o.opened - 730) AS n_postnr_24m,
       count(DISTINCT left(a.postnr,2)) FILTER (WHERE a.dato >= o.opened - 730) AS n_postnr2_24m,
       count(DISTINCT a.postnr) FILTER (WHERE a.dato >= o.opened - 365) AS n_postnr_12m,
       count(DISTINCT left(a.postnr,2)) FILTER (WHERE a.dato >= o.opened - 365) AS n_postnr2_12m,
       min(a.postnr) FILTER (WHERE a.dato >= o.opened - 730) AS min_postnr_24m,
       max(a.postnr) FILTER (WHERE a.dato >= o.opened - 730) AS max_postnr_24m
FROM o LEFT JOIN kunngjoring.adresse a ON a.orgnr=o.orgnr AND a.dato < o.opened AND a.kilde IN ('ny','gjeldende') AND nullif(trim(a.postnr),'') IS NOT NULL
GROUP BY 1 ORDER BY 1;
