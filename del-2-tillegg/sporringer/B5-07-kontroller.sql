\echo === payroll_dekning_kohort ===
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT count(*) AS rader, count(a.total_assets) AS har_ta, count(a.payroll_expenses) AS har_payroll,
       count(a.employee_count) AS har_ansatte, count(a.operating_revenue) AS har_driftsinnt
FROM o JOIN company_intel.annual_account a USING (orgnr);
\echo === payroll_dekning_hele_tabellen ===
SELECT source_name, count(*) AS rader, count(payroll_expenses) AS har_payroll, count(employee_count) AS har_ansatte
FROM company_intel.annual_account GROUP BY 1 ORDER BY 2 DESC;
\echo === valuta_utliggere_kohort ===
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT a.orgnr, a.fiscal_year, a.currency, a.total_assets FROM o JOIN company_intel.annual_account a USING (orgnr)
WHERE a.currency IS NOT NULL AND a.currency <> 'NOK';
\echo === maaned_2026 ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2025-01-01' AND dato <= DATE '2026-08-24' GROUP BY 1),
f AS (SELECT a.orgnr, a.opened, EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.dato=a.opened
        AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM a)
SELECT to_char(opened,'YYYY-MM') AS mnd, count(*) AS n, count(*) FILTER (WHERE oppbud) AS n_oppbud
FROM f GROUP BY 1 ORDER BY 1;
