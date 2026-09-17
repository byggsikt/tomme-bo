-- V/10 Sletting etter utfall + skiftesamling/fordringsfrist/ny bostyrer i kohorten (verifier av B4)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt, e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr)),
s AS (SELECT c.orgnr, min(k.dato) AS slettet FROM c JOIN kunngjoring.kunngjoring k ON k.orgnr=c.orgnr AND k.type_kanon='Sletting' AND k.dato >= c.opened AND k.dato <= DATE '2026-08-24' GROUP BY 1)
SELECT 'a_sletting' AS hva, c.utfall, count(*)::text AS n, count(s.slettet)::text AS slettet,
       round(100.0*count(s.slettet)/count(*),1)::text AS pct,
       'median_utfall_til_sletting=' || coalesce((percentile_disc(0.5) WITHIN GROUP (ORDER BY s.slettet - c.utfallsdato))::text,'-') || ' samme_dag=' || count(*) FILTER (WHERE s.slettet = c.utfallsdato)::text || ' innen30d=' || count(*) FILTER (WHERE s.slettet - c.utfallsdato BETWEEN 0 AND 30)::text || ' median_aapning_til_sletting=' || coalesce((percentile_disc(0.5) WITHIN GROUP (ORDER BY s.slettet - c.opened))::text,'-') AS detalj
FROM c LEFT JOIN s USING (orgnr) GROUP BY 2
UNION ALL
SELECT 'b_signal', x.signal, count(DISTINCT x.orgnr)::text, NULL, NULL, string_agg(DISTINCT left(x.tk,60), ' ; ')
FROM (
  SELECT c.orgnr, CASE WHEN k.type_kanon ~* 'skiftesamling' THEN 'skiftesamling' WHEN k.type_kanon ~* 'fordringsfrist' THEN 'ny_fordringsfrist' WHEN k.type_kanon ~* 'fordringshavermøte' THEN 'fordringshavermote' WHEN k.type_kanon ~* 'bostyrer' THEN 'ny_bostyrer' END AS signal, k.type_kanon AS tk
  FROM c JOIN kunngjoring.kunngjoring k ON k.orgnr=c.orgnr AND k.dato >= c.opened AND k.dato <= DATE '2026-08-24'
  WHERE k.type_kanon ~* '(skiftesamling|fordringsfrist|fordringshavermøte|bostyrer)'
) x GROUP BY 2
ORDER BY 1,2;
