-- B4-07: exactly what the three outcome announcements carry in OUR corpus (cohort), field by field.
-- (a) the raw type string on every outcome announcement of the cohort: length, distinct strings, detalj coverage
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'a_raa_type' AS hva, h.type_kanon, length(h.type_raa) AS lengde_raa,
       count(*) AS rader, count(DISTINCT h.orgnr) AS selskaper,
       count(*) FILTER (WHERE coalesce(trim(h.detalj),'')<>'') AS rader_med_detalj,
       count(DISTINCT h.type_raa) AS distinkte_raa_strenger
FROM o JOIN kunngjoring.v_hendelse h ON h.orgnr=o.orgnr AND h.dato>=o.opened AND h.dato<=DATE '2026-08-24'
WHERE h.type_kanon IN ('Konkurs - åpning','Konkurs - innstilling av bobehandlingen','Konkurs - avslutning av bobehandlingen','Sletting','Fortsettelse av bobehandling')
GROUP BY 2,3 ORDER BY 2,3;

-- (b) every felt key attached to each outcome announcement type in the cohort (0 rows for a type = the announcement carries no structured field at all)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'b_felt_pr_utfallstype' AS hva, kunngjoring.kanoniser_type(f.kunngj_type) AS type_kanon, f.felt,
       count(*) AS rader, count(DISTINCT f.orgnr) AS selskaper, count(DISTINCT f.verdi) AS distinkte_verdier
FROM o JOIN kunngjoring.felt f ON f.orgnr=o.orgnr AND f.dato>=o.opened
WHERE kunngjoring.kanoniser_type(f.kunngj_type) IN ('Konkurs - åpning','Konkurs - innstilling av bobehandlingen','Konkurs - avslutning av bobehandlingen','Sletting','Fortsettelse av bobehandling')
GROUP BY 2,3 ORDER BY 2,3;

-- (c) kunngjoring.insolvens columns on the innstilling and the avslutning row (does the court data table carry anything about money?)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'c_insolvenskolonner' AS hva, i.type, count(*) AS rader, count(DISTINCT i.orgnr) AS selskaper,
       count(nullif(trim(i.tingrett),'')) AS tingrett,
       count(nullif(trim(i.bostyrer),'')) AS bostyrer,
       count(nullif(trim(i.saksnr),''))   AS saksnr,
       count(i.fristdag)                  AS fristdag,
       count(nullif(trim(i.bransje),''))  AS bransje,
       count(nullif(trim(i.kapital),''))  AS kapital
FROM o JOIN kunngjoring.insolvens i ON i.orgnr=o.orgnr AND i.dato>=o.opened AND i.dato<=DATE '2026-08-24'
GROUP BY 2 ORDER BY 3 DESC;

-- (d) full list of distinct raw type strings on the cohort's innstilling and avslutning announcements
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'd_distinkte_strenger' AS hva, k.type_kanon, k.type AS raa_streng, count(*) AS rader, count(DISTINCT k.orgnr) AS selskaper
FROM o JOIN kunngjoring.kunngjoring k ON k.orgnr=o.orgnr AND k.dato>=o.opened
WHERE k.type_kanon IN ('Konkurs - innstilling av bobehandlingen','Konkurs - avslutning av bobehandlingen')
GROUP BY 2,3 ORDER BY 2,4 DESC LIMIT 40;

-- (e) corpus-wide: how many ordinary-closure announcements exist at all (the ones that WOULD carry a dividend line at the source)
SELECT 'e_avslutning_korpus' AS hva, extract(year FROM k.dato)::int AS aar,
       count(DISTINCT k.orgnr) AS selskaper, count(*) AS rader
FROM kunngjoring.kunngjoring k WHERE k.type_kanon='Konkurs - avslutning av bobehandlingen' GROUP BY 2 ORDER BY 2;
