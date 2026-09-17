-- B4-03: the COMPLETE canonical type universe of the corpus (all 16.9M rows), so absence can be proven by reading the list.
SELECT 'type_univers' AS hva, k.type_kanon, coalesce(k.register,'<NULL>') AS register,
       count(*) AS rader, count(DISTINCT k.orgnr) AS selskaper, min(k.dato) AS forste, max(k.dato) AS siste
FROM kunngjoring.kunngjoring k GROUP BY 2,3 ORDER BY 4 DESC;
SELECT 'type_univers_total' AS hva, count(*) AS rader, count(DISTINCT k.type_kanon) AS n_typer, count(DISTINCT k.orgnr) AS selskaper,
       count(DISTINCT (k.orgnr,k.dato,k.type)) AS unike_org_dato_type FROM kunngjoring.kunngjoring k;
