-- A2/15 Er andelen med feltet stabil etter organisasjonsform?
-- MERK: company_intel.company er strippet for slettede selskaper (funn d),
-- så org_form kan være tomt for store deler av kohorten. Vi rapporterer dekningen.
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o)
SELECT coalesce(nullif(trim(c.org_form_code),''),'(tom/mangler)') AS org_form,
       count(*) AS n,
       count(*) FILTER (WHERE b.oppbud) AS n_oppbud,
       round(100.0*count(*) FILTER (WHERE b.oppbud)/count(*),1) AS pct
FROM b LEFT JOIN company_intel.company c USING (orgnr)
GROUP BY 1 ORDER BY 2 DESC LIMIT 15;
