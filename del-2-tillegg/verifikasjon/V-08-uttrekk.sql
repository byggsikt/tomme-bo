-- V/08 Per-bo uttrekk for standardisering (verifier): grunnlag, utfall, tid, siste balanse FØR åpningsåret, tingrett, bransje
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
meta AS (SELECT o.orgnr, max(nullif(trim(i.tingrett),'')) AS tingrett, max(nullif(trim(i.bransje),'')) AS bransje FROM o JOIN kunngjoring.insolvens i ON i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning' GROUP BY 1),
aa AS (SELECT DISTINCT ON (a.orgnr) a.orgnr, a.fiscal_year, a.total_assets, a.operating_revenue, coalesce(a.amount_unit,'') AS amount_unit, coalesce(a.currency,'') AS currency, a.source_name
       FROM company_intel.annual_account a JOIN o USING (orgnr)
       WHERE a.total_assets IS NOT NULL AND a.fiscal_year < extract(year FROM o.opened)::int
       ORDER BY a.orgnr, a.fiscal_year DESC, a.source_name),
anyacc AS (SELECT DISTINCT orgnr FROM company_intel.annual_account a JOIN o USING (orgnr))
SELECT o.orgnr, o.opened::text AS opened,
       CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall,
       coalesce((e.innstilt - o.opened)::text,'') AS t_inn,
       coalesce((e.avsluttet - o.opened)::text,'') AS t_avs,
       CASE WHEN EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') THEN 1 ELSE 0 END AS oppbud,
       regexp_replace(coalesce(meta.tingrett,''),'[[:space:]]+',' ','g') AS tingrett,
       regexp_replace(coalesce(meta.bransje,''),'[[:space:]]+',' ','g') AS bransje,
       coalesce(aa.fiscal_year::text,'') AS fy, coalesce(aa.total_assets::text,'') AS total_assets, coalesce(aa.operating_revenue::text,'') AS operating_revenue,
       aa.amount_unit, aa.currency, coalesce(aa.source_name,'') AS source_name,
       CASE WHEN anyacc.orgnr IS NOT NULL THEN 1 ELSE 0 END AS har_regnskap
FROM o LEFT JOIN e USING (orgnr) LEFT JOIN meta USING (orgnr) LEFT JOIN aa USING (orgnr) LEFT JOIN anyacc USING (orgnr)
ORDER BY o.orgnr;
