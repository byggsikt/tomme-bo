-- B4-04: reopenings / continuations (konkursloven s 139) and any reversal ("oppheving") events.
-- corpus-wide first, then the cohort.

-- (a) corpus: every announcement whose canonical type or detalj mentions continuation / reopening / reversal
SELECT 'a_korpus_fortsettelse' AS hva, h.type_kanon, coalesce(h.register,'<NULL>') AS register,
       count(*) AS rader, count(DISTINCT h.orgnr) AS selskaper, min(h.dato) AS forste, max(h.dato) AS siste
FROM kunngjoring.v_hendelse h
WHERE h.type_kanon ~* '(fortsettelse|gjenoppta|gjenåpn|gjenapn|opphev|omgjort|omgjøring av konkurs|tilbakekalt|annullert|ugyldig)'
   OR h.detalj    ~* '(fortsettelse av bobehandl|gjenoppta|gjenåpn|konkursen er opphev|kjennelsen er opphev|opphevet konkurs)'
GROUP BY 2,3 ORDER BY 5 DESC LIMIT 80;

-- (b) corpus: the Fortsettelse rows themselves, with the felt attached to them
SELECT 'b_fortsettelse_felt' AS hva, f.felt, left(f.verdi,120) AS verdi, count(*) AS rader, count(DISTINCT f.orgnr) AS selskaper
FROM kunngjoring.felt f
WHERE kunngjoring.kanoniser_type(f.kunngj_type) = 'Fortsettelse av bobehandling'
GROUP BY 2,3 ORDER BY 4 DESC LIMIT 40;

-- (c) corpus: for the 26 companies with a Fortsettelse announcement, the full insolvency timeline
SELECT 'c_fortsettelse_forlop' AS hva, x.orgnr, i.dato, i.type
FROM (SELECT DISTINCT orgnr FROM kunngjoring.kunngjoring WHERE type_kanon='Fortsettelse av bobehandling') x
JOIN kunngjoring.insolvens i ON i.orgnr = x.orgnr
ORDER BY 2,3;

-- (d) COHORT: which cohort estates have a continuation announcement, when, and relative to the innstilling
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, e.innstilt, e.avsluttet FROM o LEFT JOIN e USING (orgnr))
SELECT 'd_kohort_fortsettelse' AS hva, c.orgnr, c.utfall, c.opened, c.innstilt, c.avsluttet,
       min(h.dato) AS fortsettelse_dato,
       (min(h.dato) - c.opened) AS dager_fra_apning,
       (min(h.dato) - c.innstilt) AS dager_fra_innstilling
FROM c JOIN kunngjoring.v_hendelse h ON h.orgnr=c.orgnr AND h.type_kanon='Fortsettelse av bobehandling'
GROUP BY 2,3,4,5,6 ORDER BY 2;

-- (e) COHORT: any estate where an avslutning follows an innstilling (i.e. the estate came back to life and closed ordinarily)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1)
SELECT 'e_innstilt_deretter_avsluttet' AS hva,
       count(*) FILTER (WHERE innstilt IS NOT NULL) AS innstilte,
       count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL) AS innstilt_og_avsluttet,
       count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL AND avsluttet > innstilt) AS avsluttet_etter_innstilling,
       count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL AND avsluttet <= innstilt) AS avsluttet_for_eller_samme_dag
FROM e;

-- (f) the same rows listed, for reading
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1)
SELECT 'f_innstilt_deretter_avsluttet_rader' AS hva, o.orgnr, o.opened, e.innstilt, e.avsluttet, (e.avsluttet - e.innstilt) AS dager
FROM o JOIN e USING (orgnr) WHERE e.innstilt IS NOT NULL AND e.avsluttet IS NOT NULL ORDER BY 6;
