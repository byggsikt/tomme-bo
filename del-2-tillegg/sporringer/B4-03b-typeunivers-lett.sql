-- B4-03b: canonical type universe, cheap version (no count(distinct orgnr) over 19M rows)
SELECT 'type_univers' AS hva, k.type_kanon, count(*) AS rader, min(k.dato) AS forste, max(k.dato) AS siste
FROM kunngjoring.kunngjoring k GROUP BY 2 ORDER BY 3 DESC;
SELECT 'type_total' AS hva, count(*) AS rader, count(DISTINCT k.type_kanon) AS n_typer FROM kunngjoring.kunngjoring k;
-- the dimension table lists every canonical type with its semantics
SELECT 'hendelsestype_dim' AS hva, t.type_kanon, t.kategori, t.er_livslopslutt, t.er_insolvensspor, coalesce(t.utfall,'') AS utfall
FROM kunngjoring.hendelsestype t ORDER BY 3,2;
