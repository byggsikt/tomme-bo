-- V-B1-01: is ABSENCE of «Åpnet etter» a signal, or a parse/date artifact? (read-only)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
, flags AS (
  SELECT o.orgnr, o.opened,
    EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened
              AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter')            AS opp_on_opened,
    EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr
              AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter')            AS opp_any_date,
    EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened
              AND x.kunngj_type='Konkurs - åpning')                                     AS any_felt_on_opened,
    EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened
              AND x.kunngj_type='Konkurs - åpning' AND x.felt IN ('Konkurs åpnet','Bransje/stilling')) AS anchor_on_opened,
    (SELECT count(DISTINCT i.dato) FROM kunngjoring.insolvens i
       WHERE i.orgnr=o.orgnr AND i.type='Konkurs - åpning')                             AS n_open_dates
  FROM o)
SELECT 'A_cohort'                       AS q, count(*)::text AS v1, ''::text AS v2 FROM flags
UNION ALL SELECT 'B_opp_on_opened',      count(*) FILTER (WHERE opp_on_opened)::text, '' FROM flags
UNION ALL SELECT 'B_opp_any_date',       count(*) FILTER (WHERE opp_any_date)::text, '' FROM flags
UNION ALL SELECT 'B_drift_gained',       count(*) FILTER (WHERE opp_any_date AND NOT opp_on_opened)::text, '' FROM flags
UNION ALL SELECT 'C_any_felt_on_opened', count(*) FILTER (WHERE any_felt_on_opened)::text, '' FROM flags
UNION ALL SELECT 'C_anchor_on_opened',   count(*) FILTER (WHERE anchor_on_opened)::text, '' FROM flags
UNION ALL SELECT 'C_no_anchor_row',      count(*) FILTER (WHERE NOT anchor_on_opened)::text, '' FROM flags
UNION ALL SELECT 'D_notoppbud_with_anchor',    count(*) FILTER (WHERE NOT opp_on_opened AND anchor_on_opened)::text, '' FROM flags
UNION ALL SELECT 'D_notoppbud_without_anchor', count(*) FILTER (WHERE NOT opp_on_opened AND NOT anchor_on_opened)::text, '' FROM flags
UNION ALL SELECT 'E_open_dates_'||n_open_dates::text, count(*)::text, '' FROM flags GROUP BY n_open_dates
ORDER BY 1;
