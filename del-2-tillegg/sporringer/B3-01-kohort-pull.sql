-- B3 (construction mechanism): one row per cohort estate with outcome, petition basis, court, industry label,
-- last filed accounts BEFORE the opening year, founding date and registered capital. READ-ONLY.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet
      FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, e.innstilt, e.avsluttet
      FROM o LEFT JOIN e USING (orgnr)),
attr AS (SELECT DISTINCT ON (i.orgnr) i.orgnr,
                replace(replace(nullif(trim(i.bransje),''), E'\r', ''), E'\n', '<NL>') AS bransje,
                nullif(trim(i.tingrett),'') AS tingrett, i.fristdag
         FROM kunngjoring.insolvens i JOIN c ON c.orgnr=i.orgnr AND i.dato=c.opened WHERE i.type='Konkurs - åpning' ORDER BY i.orgnr, i.bransje),
opp AS (SELECT c.orgnr, EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=c.orgnr AND x.dato=c.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM c),
acc AS (SELECT a.orgnr, a.fiscal_year, a.source_name, coalesce(a.amount_unit,'') AS amount_unit, coalesce(a.currency,'') AS currency,
               a.total_assets, a.current_assets, a.equity, a.liabilities, a.current_liabilities, a.operating_revenue, a.operating_result, a.annual_result, a.payroll_expenses, a.employee_count,
               row_number() OVER (PARTITION BY a.orgnr ORDER BY a.fiscal_year DESC, (a.source_name='brreg-regnskap') DESC) AS rn,
               count(*) OVER (PARTITION BY a.orgnr) AS n_acc_before
        FROM company_intel.annual_account a JOIN c ON a.orgnr=c.orgnr::text
        WHERE a.fiscal_year < extract(year FROM c.opened)),
accany AS (SELECT a.orgnr, count(*) AS n_acc_any, max(a.fiscal_year) AS max_fy_any FROM company_intel.annual_account a JOIN c ON a.orgnr=c.orgnr::text GROUP BY 1),
sel AS (SELECT s.orgnr, s.stiftet, s.kapital_ved_reg, s.kapital_siste FROM kunngjoring.selskap s JOIN c USING (orgnr)),
varsel AS (SELECT c.orgnr, count(*) AS n_varsel_for FROM c JOIN kunngjoring.insolvens v ON v.orgnr=c.orgnr AND v.type='Varsel om tvangsoppløsning' AND v.dato < c.opened GROUP BY 1)
SELECT c.orgnr, c.opened, c.utfall, c.innstilt, c.avsluttet, attr.bransje, attr.tingrett, attr.fristdag, opp.oppbud,
       acc.fiscal_year, acc.source_name, acc.amount_unit, acc.currency, acc.total_assets, acc.current_assets, acc.equity, acc.liabilities, acc.current_liabilities,
       acc.operating_revenue, acc.operating_result, acc.annual_result, acc.payroll_expenses, acc.employee_count, acc.n_acc_before,
       coalesce(accany.n_acc_any,0) AS n_acc_any, accany.max_fy_any,
       sel.stiftet, sel.kapital_ved_reg, sel.kapital_siste, coalesce(varsel.n_varsel_for,0) AS n_varsel_for
FROM c LEFT JOIN attr ON attr.orgnr=c.orgnr LEFT JOIN opp ON opp.orgnr=c.orgnr
       LEFT JOIN acc ON acc.orgnr=c.orgnr::text AND acc.rn=1
       LEFT JOIN accany ON accany.orgnr=c.orgnr::text
       LEFT JOIN sel ON sel.orgnr=c.orgnr LEFT JOIN varsel ON varsel.orgnr=c.orgnr
ORDER BY c.orgnr;
