-- B4-04b: continuations / reopenings / reversals, cheap version (raw type column only, no view)
-- (a) corpus: every raw type string that mentions continuation, reopening or reversal
SELECT 'a_korpus_treff' AS hva, k.type_kanon, count(*) AS rader, count(DISTINCT k.orgnr) AS selskaper, min(k.dato) AS forste, max(k.dato) AS siste
FROM kunngjoring.kunngjoring k
WHERE k.type ~* '(fortsettelse av bobehandl|gjenoppta|gjenåpn|opphev|omgjort|omgjøring av konkurs|tilbakekalt|annullert)'
GROUP BY 2 ORDER BY 4 DESC LIMIT 60;

-- (b) the full insolvency timeline of every company that ever had a Fortsettelse announcement
SELECT 'b_fortsettelse_forlop' AS hva, x.orgnr, i.dato, i.type
FROM (SELECT DISTINCT orgnr FROM kunngjoring.kunngjoring WHERE type_kanon='Fortsettelse av bobehandling') x
JOIN kunngjoring.insolvens i ON i.orgnr = x.orgnr
ORDER BY 2,3;

-- (c) COHORT: the continuation announcements, with timing relative to the outcome
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, e.innstilt, e.avsluttet FROM o LEFT JOIN e USING (orgnr))
SELECT 'c_kohort_fortsettelse' AS hva, c.orgnr, c.utfall, c.opened, c.innstilt, c.avsluttet,
       min(k.dato) AS fortsettelse_dato, (min(k.dato) - c.opened) AS dager_fra_apning, (min(k.dato) - c.innstilt) AS dager_fra_innstilling
FROM c JOIN kunngjoring.kunngjoring k ON k.orgnr=c.orgnr AND k.type_kanon='Fortsettelse av bobehandling'
GROUP BY 2,3,4,5,6 ORDER BY 2;

-- (d) how often does an innstilling get followed by an avslutning in the cohort (the estate came back)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1)
SELECT 'd_innstilt_og_avsluttet' AS hva,
       count(*) FILTER (WHERE innstilt IS NOT NULL) AS innstilte,
       count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL) AS ogsa_avsluttet,
       count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL AND avsluttet > innstilt) AS avsluttet_etter_innstilling,
       count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL AND avsluttet < innstilt) AS avsluttet_for_innstilling,
       count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL AND avsluttet = innstilt) AS samme_dag
FROM e;

-- (e) list those rows
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1)
SELECT 'e_rader' AS hva, o.orgnr, o.opened, e.innstilt, e.avsluttet, (e.avsluttet-e.innstilt) AS dager
FROM o JOIN e USING (orgnr) WHERE e.innstilt IS NOT NULL AND e.avsluttet IS NOT NULL ORDER BY 6;

-- (f) corpus: any announcement at all whose raw type mentions "opphev" (reversal by the Court of Appeal)
SELECT 'f_opphev' AS hva, left(k.type,80) AS type_raa, count(*) AS rader, count(DISTINCT k.orgnr) AS selskaper, min(k.dato) AS forste, max(k.dato) AS siste
FROM kunngjoring.kunngjoring k WHERE k.type ~* 'opphev' GROUP BY 2 ORDER BY 4 DESC LIMIT 30;
