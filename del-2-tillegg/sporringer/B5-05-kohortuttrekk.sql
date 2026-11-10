-- B5/05 Per-bo uttrekk av kohorten (5 165) med grunnlag, tingrett, bransjeetikett og siste balanse FØR åpningsåret.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
meta AS (SELECT o.orgnr, o.opened,
                max(nullif(trim(i.tingrett),''))  AS tingrett,
                max(nullif(trim(i.bransje),''))   AS bransje,
                max(nullif(trim(i.bostyrer),''))  AS bostyrer
         FROM o JOIN kunngjoring.insolvens i ON i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning'
         GROUP BY 1,2),
e AS (SELECT i.orgnr,
             min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
             min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
      FROM kunngjoring.insolvens i JOIN o USING (orgnr)
      WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
aa AS (SELECT DISTINCT ON (a.orgnr) a.orgnr, a.fiscal_year, a.total_assets, a.equity, a.liabilities,
              a.current_assets, a.current_liabilities, a.operating_revenue, a.payroll_expenses,
              coalesce(a.amount_unit,'<NULL>') AS amount_unit, a.currency, a.source_name
       FROM company_intel.annual_account a JOIN o USING (orgnr)
       WHERE a.total_assets IS NOT NULL
         AND a.fiscal_year < extract(year FROM o.opened)::int
       ORDER BY a.orgnr, a.fiscal_year DESC, a.source_name)
SELECT o.orgnr, o.opened,
       CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt'
            WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall,
       coalesce((CASE WHEN e.innstilt IS NOT NULL THEN e.innstilt - o.opened
                      WHEN e.avsluttet IS NOT NULL THEN e.avsluttet - o.opened END)::text,'') AS t_dager,
       CASE WHEN EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                           AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') THEN 'oppbud' ELSE 'ingen_felt' END AS grunnlag,
       regexp_replace(coalesce(meta.tingrett,''),'[
	]+',' ','g') AS tingrett,
       regexp_replace(coalesce(meta.bransje,''),'[
	]+',' ','g') AS bransje,
       coalesce(aa.fiscal_year::text,'') AS fy,
       coalesce(aa.total_assets::text,'') AS total_assets,
       coalesce(aa.equity::text,'') AS equity,
       coalesce(aa.liabilities::text,'') AS liabilities,
       coalesce(aa.operating_revenue::text,'') AS operating_revenue,
       coalesce(aa.payroll_expenses::text,'') AS payroll_expenses,
       coalesce(aa.amount_unit,'') AS amount_unit,
       coalesce(aa.currency,'') AS currency,
       coalesce(aa.source_name,'') AS source_name,
       (DATE '2026-08-24' - o.opened) AS oppfolging
FROM o LEFT JOIN e USING (orgnr) LEFT JOIN meta USING (orgnr) LEFT JOIN aa USING (orgnr)
ORDER BY o.orgnr;
