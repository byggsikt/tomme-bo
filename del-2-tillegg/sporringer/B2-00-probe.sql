-- B2 probe: PG version, unit-rule evidence, «Utgår» fields, «Revisjon av årsregnskap» detail, «Godkjent årsregnskap» month profile, «Varsel» detail
SELECT 'version' AS hva, version();
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'unit_x_source' AS hva, a.source_name, coalesce(a.amount_unit,'<NULL>') AS amount_unit, coalesce(a.currency,'<NULL>') AS currency, count(*) AS rader, count(DISTINCT a.orgnr) AS selskaper,
       count(*) FILTER (WHERE a.total_assets % 1000 = 0) AS ta_mult_1000, count(*) FILTER (WHERE a.total_assets % 1000 <> 0) AS ta_not_mult_1000,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY a.total_assets) AS med_ta
FROM o JOIN company_intel.annual_account a ON a.orgnr=o.orgnr::text GROUP BY 2,3,4 ORDER BY 2,3,4;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'unit_pairs' AS hva, count(*) AS par, count(*) FILTER (WHERE a1.total_assets = a2.total_assets) AS ta_lik, count(*) FILTER (WHERE a1.equity = a2.equity) AS ek_lik, count(*) FILTER (WHERE a1.operating_revenue = a2.operating_revenue) AS inntekt_lik,
       count(*) FILTER (WHERE a1.operating_revenue IS NULL OR a2.operating_revenue IS NULL) AS inntekt_null
FROM o JOIN company_intel.annual_account a1 ON a1.orgnr=o.orgnr::text AND a1.source_name='brreg-recovered'
       JOIN company_intel.annual_account a2 ON a2.orgnr=a1.orgnr AND a2.fiscal_year=a1.fiscal_year AND a2.source_name='brreg-regnskap';
SELECT 'unit_values_corpus' AS hva, coalesce(amount_unit,'<NULL>') AS amount_unit, source_name, count(*) FROM company_intel.annual_account GROUP BY 2,3 ORDER BY 4 DESC;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'utgaar_felt' AS hva, kunngjoring.kanoniser_type(f.kunngj_type) AS kt, f.felt, left(f.verdi,30) AS verdi, count(*) AS rader, count(DISTINCT f.orgnr) AS selskaper
FROM o JOIN kunngjoring.felt f ON f.orgnr=o.orgnr AND f.dato < o.opened WHERE f.felt IN ('Daglig leder','Revisor') AND f.verdi ILIKE 'Utg%' GROUP BY 2,3,4 ORDER BY 5 DESC;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'revisjon_detalj' AS hva, left(h.detalj,90) AS detalj, count(*) AS rader, count(DISTINCT h.orgnr) AS selskaper FROM o JOIN kunngjoring.v_hendelse h ON h.orgnr=o.orgnr AND h.dato < o.opened AND h.type_kanon='Revisjon av årsregnskap' GROUP BY 2 ORDER BY 3 DESC LIMIT 8;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'godkjent_detalj' AS hva, left(h.detalj,80) AS detalj, count(*) AS rader FROM o JOIN kunngjoring.v_hendelse h ON h.orgnr=o.orgnr AND h.dato < o.opened AND h.type_kanon='Godkjent årsregnskap' GROUP BY 2 ORDER BY 3 DESC LIMIT 5;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'godkjent_maaned' AS hva, extract(month FROM h.dato)::int AS mnd, count(DISTINCT (h.orgnr, h.dato)) AS kunngj FROM o JOIN kunngjoring.v_hendelse h ON h.orgnr=o.orgnr AND h.dato < o.opened AND h.dato >= DATE '2018-01-01' AND h.type_kanon='Godkjent årsregnskap' AND h.register='Regnskapsregisteret' GROUP BY 2 ORDER BY 2;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'varsel_detalj' AS hva, h.register, left(h.detalj,100) AS detalj, count(*) AS rader FROM o JOIN kunngjoring.v_hendelse h ON h.orgnr=o.orgnr AND h.dato < o.opened AND h.type_kanon='Varsel om tvangsoppløsning' GROUP BY 2,3 ORDER BY 4 DESC LIMIT 8;
