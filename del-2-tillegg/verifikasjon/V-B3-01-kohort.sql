-- V-B3 (ADVERSARIAL VERIFICATION of B3): independent cohort pull.
-- One row per cohort estate: outcome, dates, petition basis, court, industry label,
-- last filed accounts with fiscal_year < opening year, founding date. READ-ONLY (SELECT/WITH only).
WITH o AS (
  SELECT orgnr, min(dato) AS opened
  FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31'
  GROUP BY 1),
e AS (
  SELECT i.orgnr,
         min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
         min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
  FROM kunngjoring.insolvens i JOIN o USING (orgnr)
  WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24'
  GROUP BY 1),
c AS (
  SELECT o.orgnr, o.opened,
         CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt'
              WHEN e.avsluttet IS NOT NULL THEN 'avsluttet'
              ELSE 'aapen' END AS utfall,
         e.innstilt, e.avsluttet
  FROM o LEFT JOIN e USING (orgnr)),
-- industry/court from the opening row; count how many distinct labels exist that day (ambiguity check)
attr AS (
  SELECT c.orgnr,
         min(replace(replace(nullif(trim(i.bransje),''), E'\r',''), E'\n','<NL>')) AS bransje,
         count(DISTINCT nullif(trim(i.bransje),'')) AS n_bransje,
         min(nullif(trim(i.tingrett),'')) AS tingrett,
         count(DISTINCT nullif(trim(i.tingrett),'')) AS n_tingrett,
         count(*) AS n_apningsrader
  FROM kunngjoring.insolvens i JOIN c ON c.orgnr=i.orgnr AND i.dato=c.opened AND i.type='Konkurs - åpning'
  GROUP BY 1),
opp AS (
  SELECT c.orgnr,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=c.orgnr AND x.dato=c.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM c),
acc AS (
  SELECT a.orgnr, a.fiscal_year, a.source_name, coalesce(a.amount_unit,'') AS amount_unit,
         coalesce(a.currency,'') AS currency,
         a.total_assets, a.current_assets, a.equity, a.liabilities, a.current_liabilities,
         a.operating_revenue, a.operating_result, a.annual_result, a.payroll_expenses, a.employee_count,
         row_number() OVER (PARTITION BY a.orgnr
                            ORDER BY a.fiscal_year DESC, (a.source_name='brreg-regnskap') DESC, a.id) AS rn,
         count(*)       OVER (PARTITION BY a.orgnr) AS n_acc_before,
         min(a.fiscal_year) OVER (PARTITION BY a.orgnr) AS min_fy_before
  FROM company_intel.annual_account a
  JOIN c ON a.orgnr = trim(c.orgnr)
  WHERE a.fiscal_year < extract(year FROM c.opened)),
accany AS (
  SELECT a.orgnr, count(*) AS n_acc_any, max(a.fiscal_year) AS max_fy_any
  FROM company_intel.annual_account a JOIN c ON a.orgnr = trim(c.orgnr) GROUP BY 1),
sel AS (SELECT s.orgnr, s.stiftet FROM kunngjoring.selskap s JOIN c USING (orgnr))
SELECT trim(c.orgnr) AS orgnr, c.opened, c.utfall, c.innstilt, c.avsluttet,
       attr.bransje, attr.n_bransje, attr.tingrett, attr.n_tingrett, attr.n_apningsrader,
       opp.oppbud,
       acc.fiscal_year, acc.source_name, acc.amount_unit, acc.currency,
       acc.total_assets, acc.current_assets, acc.equity, acc.liabilities, acc.current_liabilities,
       acc.operating_revenue, acc.operating_result, acc.annual_result, acc.payroll_expenses, acc.employee_count,
       coalesce(acc.n_acc_before,0) AS n_acc_before, acc.min_fy_before,
       coalesce(accany.n_acc_any,0) AS n_acc_any, accany.max_fy_any,
       sel.stiftet
FROM c
LEFT JOIN attr   ON attr.orgnr = c.orgnr
LEFT JOIN opp    ON opp.orgnr  = c.orgnr
LEFT JOIN acc    ON acc.orgnr  = trim(c.orgnr) AND acc.rn = 1
LEFT JOIN accany ON accany.orgnr = trim(c.orgnr)
LEFT JOIN sel    ON sel.orgnr  = c.orgnr
ORDER BY 1;
