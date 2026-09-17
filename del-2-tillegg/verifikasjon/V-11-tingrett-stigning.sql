-- V/11 Steg oppbudsandelen i hver domstol 2023 -> 2026 (t.o.m. 24.08)? Rå domstolsnavn, n >= 40 begge år (verifier av B5 § 1.4)
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-01-01' AND '2026-08-24' GROUP BY 1),
m AS (SELECT a.orgnr, a.opened, extract(year FROM a.opened)::int AS aar, regexp_replace(max(nullif(trim(i.tingrett),'')),'[[:space:]]+',' ','g') AS tingrett,
        EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.dato=a.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
      FROM a JOIN kunngjoring.insolvens i ON i.orgnr=a.orgnr AND i.dato=a.opened AND i.type='Konkurs - åpning' GROUP BY 1,2,3),
t AS (SELECT tingrett, aar, count(*) AS n, count(*) FILTER (WHERE oppbud) AS k FROM m GROUP BY 1,2),
p AS (SELECT t23.tingrett, t23.n AS n23, t23.k AS k23, t26.n AS n26, t26.k AS k26, round(100.0*t23.k/t23.n,1) AS pct23, round(100.0*t26.k/t26.n,1) AS pct26
      FROM t t23 JOIN t t26 ON t26.tingrett=t23.tingrett AND t26.aar=2026 WHERE t23.aar=2023 AND t23.n >= 40 AND t26.n >= 40)
SELECT 'domstol' AS hva, tingrett, n23::text, pct23::text, n26::text, pct26::text, (pct26-pct23)::text AS diff_pp FROM p
UNION ALL
SELECT 'oppsummering', 'n_domstoler=' || count(*)::text, 'steg=' || count(*) FILTER (WHERE pct26 > pct23)::text, 'falt=' || count(*) FILTER (WHERE pct26 < pct23)::text, 'uendret=' || count(*) FILTER (WHERE pct26 = pct23)::text, NULL, NULL FROM p
UNION ALL
SELECT 'antall_domstolsnavn', aar::text, count(DISTINCT tingrett)::text, NULL, NULL, NULL, NULL FROM t GROUP BY 2
ORDER BY 1,2;
