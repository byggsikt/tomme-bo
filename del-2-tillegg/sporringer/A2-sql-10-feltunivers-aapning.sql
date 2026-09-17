-- A2/10 Fullt feltinventar på ALLE «Konkurs - åpning» i korpuset: finnes det
-- noe annet felt som navngir hvem som begjærte?
SELECT felt, count(*) AS n, count(DISTINCT orgnr) AS n_selskap
FROM kunngjoring.felt WHERE kunngj_type='Konkurs - åpning'
GROUP BY 1 ORDER BY 2 DESC LIMIT 40;
