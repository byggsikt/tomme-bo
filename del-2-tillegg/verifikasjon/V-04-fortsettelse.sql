-- V/04 Gjenopptakelse etter innstilling (verifier)
-- (a) korpus
SELECT 'a_korpus_fortsettelse' AS hva, count(*)::text AS rader, count(DISTINCT orgnr)::text AS selskaper, min(dato)::text AS forste, max(dato)::text AS siste, NULL AS x
FROM kunngjoring.kunngjoring WHERE type_kanon='Fortsettelse av bobehandling'
UNION ALL
SELECT 'a_korpus_fortsettelse_tom_24aug2026', count(*)::text, count(DISTINCT orgnr)::text, min(dato)::text, max(dato)::text, NULL
FROM kunngjoring.kunngjoring WHERE type_kanon='Fortsettelse av bobehandling' AND dato <= DATE '2026-08-24';
-- (b) kohort
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet,
      count(DISTINCT i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS n_innstillingsdatoer
      FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, e.innstilt, e.avsluttet, coalesce(e.n_innstillingsdatoer,0) AS n_innst FROM o LEFT JOIN e USING (orgnr)),
f AS (SELECT c.orgnr, min(k.dato) AS forts_forste, count(DISTINCT k.dato) AS n_forts FROM c JOIN kunngjoring.kunngjoring k ON k.orgnr=c.orgnr AND k.type_kanon='Fortsettelse av bobehandling' AND k.dato >= c.opened AND k.dato <= DATE '2026-08-24' GROUP BY 1)
SELECT 'b_kohort' AS hva,
       (SELECT count(*) FROM f)::text AS bo_med_fortsettelse,
       (SELECT count(*) FROM f JOIN c USING (orgnr) WHERE c.utfall='innstilt')::text AS derav_innstilt,
       (SELECT count(*) FROM f JOIN c USING (orgnr) WHERE c.innstilt IS NOT NULL AND f.forts_forste > c.innstilt)::text AS forts_etter_innstilling,
       (SELECT count(*) FROM c WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL AND avsluttet > innstilt)::text AS innstilt_senere_avsluttet,
       (SELECT count(*) FROM c WHERE n_innst >= 2)::text AS innstilt_to_ganger
UNION ALL
SELECT 'b_rader_forts', f.orgnr, c.utfall || ' ' || c.opened::text, 'innstilt ' || coalesce(c.innstilt::text,'-'), 'forts ' || f.forts_forste::text || ' (+' || coalesce((f.forts_forste - c.innstilt)::text,'-') || ' d), n_forts=' || f.n_forts::text, 'avsl ' || coalesce(c.avsluttet::text,'-') || ' n_innst=' || c.n_innst::text
FROM f JOIN c USING (orgnr) ORDER BY 1,2;
-- (c) hele korpuset: innstilte bo (første innstilling <= 2024-12-31 slik at alle har >= 601 d) som senere fikk avslutning
WITH i AS (SELECT orgnr, min(dato) AS innst FROM kunngjoring.insolvens WHERE type='Konkurs - innstilling av bobehandlingen' AND dato BETWEEN '2023-08-25' AND '2024-12-31' GROUP BY 1),
a AS (SELECT i.orgnr, i.innst, min(x.dato) AS avsl FROM i JOIN kunngjoring.insolvens x ON x.orgnr=i.orgnr AND x.type='Konkurs - avslutning av bobehandlingen' AND x.dato > i.innst GROUP BY 1,2)
SELECT 'c_korpus_innstilt_2023_2024' AS hva, (SELECT count(*) FROM i)::text, (SELECT count(*) FROM a)::text AS senere_avsluttet, (SELECT percentile_disc(0.5) WITHIN GROUP (ORDER BY avsl-innst) FROM a)::text AS median_dager, (SELECT min(avsl-innst) FROM a)::text || '-' || (SELECT max(avsl-innst) FROM a)::text AS spenn, NULL;
