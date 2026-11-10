-- B4-01: the COMPLETE felt-key universe of the whole corpus (17.7M key/value pairs), with row and company counts.
-- Purpose: prove exhaustively which keys exist at all -- and that no key carries dividend/utlodning/payout information.
SELECT 'felt_univers' AS hva, f.felt, count(*) AS rader, count(DISTINCT f.orgnr) AS selskaper,
       count(DISTINCT f.verdi) AS n_distinkte_verdier, min(f.dato) AS forste, max(f.dato) AS siste
FROM kunngjoring.felt f GROUP BY 2 ORDER BY 3 DESC;
SELECT 'felt_total' AS hva, count(*) AS rader, count(DISTINCT f.felt) AS n_nokler, count(DISTINCT f.orgnr) AS selskaper FROM kunngjoring.felt f;
