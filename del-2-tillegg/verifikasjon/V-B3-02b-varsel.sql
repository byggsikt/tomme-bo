-- V-B3: count of "Varsel om tvangsoppløsning" strictly before the opening date, per cohort estate. READ-ONLY.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT trim(o.orgnr) AS orgnr,
       count(v.*) FILTER (WHERE v.type='Varsel om tvangsoppløsning' AND v.dato < o.opened) AS n_varsel_for
FROM o LEFT JOIN kunngjoring.insolvens v ON v.orgnr=o.orgnr
GROUP BY 1 ORDER BY 1;
